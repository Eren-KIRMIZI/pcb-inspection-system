"""AOI Engine 2.0 / adım 21-22: uygulama içi model değerlendirmesi.

Gerçek YOLO ağırlıkları ve gerçek test split'i (686 görüntü / 663 kutu)
üzerinde çalışır. Metrikler uygulamanın kullandığı sınıf eşikleri uygulandıktan
sonra üretilir; mock çıktısından metrik türetilmez.

Eşleştirme COCO benzeridir: sınıf başına, güven azalan sırayla, aynı görselde
henüz eşleşmemiş ground truth kutusuna ``IoU >= eşik`` ile bire-bir atama.
``overall`` içindeki AP değerleri, test split'inde ground truth bulunan
sınıfların ortalamasıdır; ground truth içermeyen sınıflar mAP ortalamasına
sokulmaz ve ``classes_without_ground_truth`` içinde açıkça bildirilir.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from ..config import settings
from ..schemas import (
    ClassEvaluation,
    Detection,
    EvaluationScore,
    ModelEvaluation,
)

IOU_THRESHOLDS: tuple[float, ...] = tuple(
    round(0.50 + 0.05 * index, 2) for index in range(10)
)
MATCH_IOU = 0.50
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")

Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class GroundTruthBox:
    class_id: int
    bbox: Box


@dataclass(frozen=True)
class ImageSample:
    image_path: Path
    ground_truth: tuple[GroundTruthBox, ...]


@dataclass(frozen=True)
class Prediction:
    class_id: int
    confidence: float
    bbox: Box


def yolo_to_xyxy(
    values: tuple[float, float, float, float], width: int, height: int
) -> Box:
    """YOLO normalize ``cx, cy, w, h`` değerini ``x1, y1, x2, y2`` yapar."""

    cx, cy, box_w, box_h = values
    return (
        (cx - box_w / 2) * width,
        (cy - box_h / 2) * height,
        (cx + box_w / 2) * width,
        (cy + box_h / 2) * height,
    )


def read_yolo_labels(
    path: Path, width: int, height: int, class_count: int | None = None
) -> tuple[GroundTruthBox, ...]:
    """YOLO etiket dosyasını okur; aralık dışı sınıf kimliklerini atlar."""

    if not path.exists():
        return ()
    boxes: list[GroundTruthBox] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        try:
            class_id = int(parts[0])
            values = tuple(float(item) for item in parts[1:])  # type: ignore[assignment]
        except ValueError:
            continue
        if class_count is not None and not 0 <= class_id < class_count:
            continue
        boxes.append(GroundTruthBox(class_id, yolo_to_xyxy(values, width, height)))
    return tuple(boxes)


def load_dataset_split(
    images_dir: Path, labels_dir: Path, class_count: int | None = None
) -> tuple[ImageSample, ...]:
    """Görsel/etiket çiftlerini sıralı şekilde yükler (etiketsiz görsel = boş GT)."""

    samples: list[ImageSample] = []
    for image_path in sorted(images_dir.iterdir()):
        if image_path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        height, width = image.shape[:2]
        label_path = labels_dir / f"{image_path.stem}.txt"
        samples.append(
            ImageSample(
                image_path=image_path,
                ground_truth=read_yolo_labels(label_path, width, height, class_count),
            )
        )
    return tuple(samples)


def iou(first: Box, second: Box) -> float:
    """İki ``xyxy`` kutusunun kesişme/birleşme oranı."""

    ix1 = max(first[0], second[0])
    iy1 = max(first[1], second[1])
    ix2 = min(first[2], second[2])
    iy2 = min(first[3], second[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    area_first = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    area_second = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = area_first + area_second - intersection
    return intersection / union if union > 0 else 0.0


def _match_class(
    samples: tuple[ImageSample, ...],
    predictions: tuple[tuple[Prediction, ...], ...],
    class_id: int,
    iou_threshold: float,
) -> tuple[int, tuple[bool, ...]]:
    """Sınıf için güven sıralı TP/FP bayrakları ve GT sayısını döndürür."""

    total_gt = sum(
        1 for sample in samples for item in sample.ground_truth if item.class_id == class_id
    )
    flags: list[bool] = []
    for sample, image_predictions in zip(samples, predictions):
        boxes = [item for item in sample.ground_truth if item.class_id == class_id]
        used = [False] * len(boxes)
        ordered = sorted(
            (item for item in image_predictions if item.class_id == class_id),
            key=lambda item: item.confidence,
            reverse=True,
        )
        for prediction in ordered:
            best_iou, best_index = 0.0, -1
            for index, box in enumerate(boxes):
                if used[index]:
                    continue
                value = iou(prediction.bbox, box.bbox)
                if value > best_iou:
                    best_iou, best_index = value, index
            if best_index >= 0 and best_iou >= iou_threshold:
                used[best_index] = True
                flags.append(True)
            else:
                flags.append(False)
    return total_gt, tuple(flags)


def _average_precision(total_gt: int, flags: tuple[bool, ...]) -> float:
    """Tüm doğruluk noktaları üzerinden PR eğrisi alanı (all-point AP)."""

    if total_gt == 0:
        return 0.0
    true_positives = 0
    area = 0.0
    for rank, is_true_positive in enumerate(flags, start=1):
        if is_true_positive:
            true_positives += 1
            area += true_positives / rank
    return area / total_gt


def _score(total_gt: int, flags: tuple[bool, ...]) -> EvaluationScore:
    true_positives = sum(1 for flag in flags if flag)
    false_positives = len(flags) - true_positives
    false_negatives = max(0, total_gt - true_positives)
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )
    recall = true_positives / total_gt if total_gt else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return EvaluationScore(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        ap50=round(_average_precision(total_gt, flags), 4),
        ap50_95=0.0,  # sınıf bazlı hesapta aşağıda doldurulur
        tp=true_positives,
        fp=false_positives,
        fn=false_negatives,
    )


def compute_metrics(
    samples: tuple[ImageSample, ...],
    predictions: tuple[tuple[Prediction, ...], ...],
    class_names: dict[int, str],
) -> tuple[EvaluationScore, list[dict[str, object]]]:
    """Sınıf bazlı ve genel metrikleri hesaplar.

    İkinci dönüş değeri, ``ClassEvaluation`` oluşturmak için ham sözlüklerdir;
    API şemaları ile saf metrik modülünü ayırmak için pydantic burada kullanılmaz.
    """

    if len(samples) != len(predictions):
        raise ValueError("Görsel ve tahmin listeleri aynı uzunlukta olmalı")

    class_ids = sorted(
        set(class_names)
        | {item.class_id for sample in samples for item in sample.ground_truth}
        | {item.class_id for image in predictions for item in image}
    )
    rows: list[dict[str, object]] = []
    for class_id in class_ids:
        total_gt, flags = _match_class(samples, predictions, class_id, MATCH_IOU)
        score = _score(total_gt, flags)
        ap_values = []
        for threshold in IOU_THRESHOLDS:
            _, flags_at_threshold = _match_class(
                samples, predictions, class_id, threshold
            )
            ap_values.append(_average_precision(total_gt, flags_at_threshold))
        score.ap50_95 = round(float(np.mean(ap_values)), 4)
        rows.append(
            {
                "class_name": class_names.get(class_id, str(class_id)),
                "support": total_gt,
                **score.model_dump(),
            }
        )

    measured = [row for row in rows if int(row["support"]) > 0]
    total_tp = sum(int(row["tp"]) for row in rows)
    total_fp = sum(int(row["fp"]) for row in rows)
    total_fn = sum(int(row["fn"]) for row in rows)
    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 0.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    overall = EvaluationScore(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        ap50=round(
            float(np.mean([float(row["ap50"]) for row in measured])) if measured else 0.0,
            4,
        ),
        ap50_95=round(
            float(np.mean([float(row["ap50_95"]) for row in measured])) if measured else 0.0,
            4,
        ),
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
    )
    return overall, rows


def load_evaluation(
    model_id: str = "solder-defect", split: str = "test"
) -> ModelEvaluation | None:
    """Gerçek ölçüm JSON'unu okur; yoksa/hatalıysa ``None`` döndürür.

    API hiçbir zaman uydurma metrik üretmez: dosya yoksa, bozuksa veya mock
    motorla üretilmişse ``measured_in_app=false`` kalır.
    """

    path = settings.evaluation_output_dir / f"{model_id}-{split}.json"
    if not path.exists():
        return None
    try:
        evaluation = ModelEvaluation.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if evaluation.engine != "real" or evaluation.model_id != model_id:
        return None
    return evaluation


def predictions_from_detections(detections: list[Detection]) -> tuple[Prediction, ...]:
    """Uygulama çıktısını metrik modülünün çıkarım formatına çevirir."""

    return tuple(
        Prediction(
            class_id=detection.class_id,
            confidence=detection.confidence,
            bbox=tuple(detection.bbox),  # type: ignore[arg-type]
        )
        for detection in detections
    )


def build_evaluation(
    samples: tuple[ImageSample, ...],
    predictions: tuple[tuple[Prediction, ...], ...],
    class_names: dict[int, str],
    *,
    model_id: str,
    model_name: str,
    engine: str,
    split: str,
    dataset: str,
    conf_threshold: float,
    class_thresholds_applied: bool,
    imgsz: int,
    tiling_enabled: bool,
    device: str,
    duration_seconds: float,
) -> ModelEvaluation:
    """Gerçek ölçüm sonucunu API/JSON şemasına dönüştürür."""

    overall, rows = compute_metrics(samples, predictions, class_names)
    ground_truth_boxes = sum(len(sample.ground_truth) for sample in samples)
    predicted_boxes = sum(len(image) for image in predictions)
    return ModelEvaluation(
        model_id=model_id,
        model_name=model_name,
        engine=engine,
        split=split,
        dataset=dataset,
        evaluated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        image_count=len(samples),
        ground_truth_boxes=ground_truth_boxes,
        predicted_boxes=predicted_boxes,
        conf_threshold=conf_threshold,
        class_thresholds_applied=class_thresholds_applied,
        imgsz=imgsz,
        tiling_enabled=tiling_enabled,
        device=device,
        duration_seconds=round(duration_seconds, 3),
        mean_inference_ms=round(duration_seconds * 1000 / len(samples), 2)
        if samples
        else 0.0,
        overall=overall,
        classes=[ClassEvaluation.model_validate(row) for row in rows],
        classes_without_ground_truth=[
            str(row["class_name"]) for row in rows if int(row["support"]) == 0
        ],
    )
