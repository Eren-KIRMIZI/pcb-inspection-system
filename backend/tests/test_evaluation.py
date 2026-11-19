"""AOI Engine 2.0 / adım 21-22: gerçek ölçüm metrikleri ve API entegrasyonu."""

import json
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.schemas import ModelEvaluation
from backend.app.services.evaluation import (
    GroundTruthBox,
    ImageSample,
    Prediction,
    build_evaluation,
    compute_metrics,
    iou,
    load_evaluation,
    load_dataset_split,
    read_yolo_labels,
    yolo_to_xyxy,
)

client = TestClient(app)
CLASS_NAMES = {0: "insufficient_solder", 1: "excess_solder", 2: "oxidation"}


def _sample(boxes: tuple[GroundTruthBox, ...]) -> ImageSample:
    return ImageSample(image_path=Path("board.jpg"), ground_truth=boxes)


def _boxes(class_id: int, *bbox: float) -> GroundTruthBox:
    return GroundTruthBox(class_id, bbox)  # type: ignore[arg-type]


def _prediction(class_id: int, confidence: float, *bbox: float) -> Prediction:
    return Prediction(class_id, confidence, bbox)  # type: ignore[arg-type]


def _evaluation() -> ModelEvaluation:
    return build_evaluation(
        (_sample((_boxes(0, 10.0, 10.0, 30.0, 30.0),)),),
        ((_prediction(0, 0.9, 10.0, 10.0, 30.0, 30.0),),),
        CLASS_NAMES,
        model_id="solder-defect",
        model_name="best.pt",
        engine="real",
        split="test",
        dataset="datasets/pcb-solder-defect-detection/final_solder",
        conf_threshold=0.228,
        class_thresholds_applied=True,
        imgsz=640,
        tiling_enabled=False,
        device="cpu",
        duration_seconds=1.5,
    )


def test_yolo_label_conversion_and_loading(tmp_path: Path) -> None:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 200 * np.ones((100, 200, 3), dtype=np.uint8))
    (tmp_path / "board.txt").write_text("0 0.5 0.5 0.2 0.2\n9 0.5 0.5 0.2 0.2\n")

    assert yolo_to_xyxy((0.5, 0.5, 0.2, 0.2), 200, 100) == (80.0, 40.0, 120.0, 60.0)
    labels = read_yolo_labels(tmp_path / "board.txt", 200, 100, class_count=9)
    assert len(labels) == 1  # sınıf 9 aralık dışı, atlandı
    assert labels[0].bbox == (80.0, 40.0, 120.0, 60.0)

    samples = load_dataset_split(tmp_path, tmp_path, class_count=9)
    assert len(samples) == 1
    assert samples[0].image_path == image
    assert len(samples[0].ground_truth) == 1


def test_iou_of_identical_and_disjoint_boxes() -> None:
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (10, 0, 20, 10)) == 0.0


def test_perfect_detection_produces_full_scores() -> None:
    samples = (_sample((_boxes(0, 10, 10, 30, 30),)),)
    predictions = ((_prediction(0, 0.9, 10, 10, 30, 30),),)

    overall, rows = compute_metrics(samples, predictions, CLASS_NAMES)

    assert (overall.precision, overall.recall, overall.f1) == (1.0, 1.0, 1.0)
    assert (overall.ap50, overall.ap50_95) == (1.0, 1.0)
    assert (overall.tp, overall.fp, overall.fn) == (1, 0, 0)
    assert len(rows) == 3  # ground truth olmayan sınıflar da raporda görünür
    assert {row["class_name"] for row in rows} == set(CLASS_NAMES.values())


def test_missing_prediction_is_false_negative() -> None:
    overall, _ = compute_metrics(
        (_sample((_boxes(0, 10, 10, 30, 30),)),), ((),), CLASS_NAMES
    )

    assert overall.tp == 0
    assert overall.fn == 1
    assert overall.recall == 0.0
    assert overall.ap50 == 0.0


def test_wrong_class_and_out_of_iou_are_false_positives() -> None:
    samples = (_sample((_boxes(0, 10, 10, 30, 30),)),)
    predictions = (
        (
            _prediction(0, 0.8, 90, 90, 100, 100),
            _prediction(1, 0.7, 10, 10, 30, 30),
        ),
    )

    overall, rows = compute_metrics(samples, predictions, CLASS_NAMES)

    assert (overall.tp, overall.fp, overall.fn) == (0, 2, 1)
    oxidation = next(row for row in rows if row["class_name"] == "oxidation")
    assert oxidation["support"] == 0
    assert oxidation["fp"] == 0
    excess = next(row for row in rows if row["class_name"] == "excess_solder")
    assert excess["fp"] == 1


def test_mean_ap_excludes_classes_without_ground_truth() -> None:
    samples = (
        _sample((_boxes(0, 10, 10, 30, 30),)),
        _sample((_boxes(1, 10, 10, 30, 30),)),
    )
    predictions = (
        (_prediction(0, 0.9, 10, 10, 30, 30),),
        (_prediction(1, 0.6, 11, 11, 31, 31),),
    )

    overall, rows = compute_metrics(samples, predictions, CLASS_NAMES)

    measured = [row for row in rows if row["support"] > 0]
    expected = float(np.mean([float(row["ap50"]) for row in measured]))
    assert overall.ap50 == round(expected, 4)
    assert overall.ap50_95 <= 1.0


def test_build_evaluation_records_provenance() -> None:
    evaluation = _evaluation()

    assert evaluation.engine == "real"
    assert evaluation.image_count == 1
    assert evaluation.ground_truth_boxes == 1
    assert evaluation.class_thresholds_applied is True
    assert evaluation.mean_inference_ms == 1500.0
    assert evaluation.classes_without_ground_truth == ["excess_solder", "oxidation"]


def test_load_evaluation_rejects_missing_mock_and_corrupt_files(tmp_path: Path) -> None:
    monkeypatch_settings = settings.evaluation_output_dir
    settings.evaluation_output_dir = tmp_path
    try:
        assert load_evaluation() is None

        evaluation = _evaluation()
        payload = evaluation.model_dump()
        (tmp_path / "solder-defect-test.json").write_text(json.dumps(payload))
        assert load_evaluation() is not None

        payload["engine"] = "mock"
        (tmp_path / "solder-defect-test.json").write_text(json.dumps(payload))
        assert load_evaluation() is None

        (tmp_path / "solder-defect-test.json").write_text("{bozuk")
        assert load_evaluation() is None
    finally:
        settings.evaluation_output_dir = monkeypatch_settings


def test_models_endpoint_reports_unmeasured_without_file(tmp_path: Path) -> None:
    original = settings.evaluation_output_dir
    settings.evaluation_output_dir = tmp_path
    try:
        body = client.get("/api/v1/models").json()
        assert body["measured_in_app"] is False
        assert body["evaluation"] is None
        assert "Precision" in body["unmeasured_metrics"]
    finally:
        settings.evaluation_output_dir = original


def test_models_endpoint_exposes_real_measurement(tmp_path: Path) -> None:
    original = settings.evaluation_output_dir
    settings.evaluation_output_dir = tmp_path
    try:
        (tmp_path / "solder-defect-test.json").write_text(
            json.dumps(_evaluation().model_dump())
        )
        body = client.get("/api/v1/models").json()

        assert body["measured_in_app"] is True
        assert body["evaluation"]["engine"] == "real"
        assert body["evaluation"]["overall"]["precision"] == 1.0
        assert len(body["evaluation"]["classes"]) == 3
        assert "Precision" not in body["unmeasured_metrics"]
        assert "Confusion matrix" in body["unmeasured_metrics"]
        assert any(
            "uygulama içi ölçüm" in model["note"]
            for model in body["models"]
            if model["id"] == "solder-defect"
        )
    finally:
        settings.evaluation_output_dir = original
