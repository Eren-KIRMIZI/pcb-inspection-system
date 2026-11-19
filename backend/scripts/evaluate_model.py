"""Gerçek kusur modelini gerçek test split'inde değerlendiren offline CLI.

Kullanım::

    .\\.venv\\Scripts\\python.exe -m backend.scripts.evaluate_model --split test

Sınıf eşikleri ``thresholds.json`` üzerinden uygulamanın ``get_detector()``
çağrısıyla uygulanır. Mock motor aktifse ölçüm reddedilir; dolayısıyla
``measured_in_app`` yalnızca gerçek model çıktısından beslenir. Sonuç ``data/evaluation/`` altına
yazılır (gitignored) ve ``GET /api/v1/models`` tarafından okunur.
"""

import argparse
import json
import time
from pathlib import Path

import yaml

from backend.app.config import BASE_DIR, settings
from backend.app.services.detector import get_detector
from backend.app.services.evaluation import (
    build_evaluation,
    load_dataset_split,
    predictions_from_detections,
)


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BASE_DIR / path


def _class_names(dataset_dir: Path) -> dict[int, str]:
    """``data.yaml`` içindeki sınıf adlarını ``{id: ad}`` olarak okur."""

    data = yaml.safe_load((dataset_dir / "data.yaml").read_text(encoding="utf-8"))
    names = data.get("names") or {}
    if isinstance(names, dict):
        return {int(key): str(value) for key, value in names.items()}
    return {index: str(value) for index, value in enumerate(names)}


def evaluate(
    dataset_dir: Path,
    split: str,
    output_dir: Path,
    limit: int | None = None,
) -> Path:
    """Değerlendirmeyi çalıştırır ve yazılan JSON dosyasının yolunu döndürür."""

    detector = get_detector()
    if detector.engine != "real":
        raise SystemExit(
            "Mock motor aktif; gerçek olmayan çıktıdan metrik üretilmez. "
            "USE_MOCK_DETECTOR=false yapıp tekrar deneyin."
        )

    names = _class_names(dataset_dir)
    samples = load_dataset_split(
        dataset_dir / "images" / split,
        dataset_dir / "labels" / split,
        class_count=len(names),
    )
    if not samples:
        raise SystemExit(f"Görsel bulunamadı: {dataset_dir / 'images' / split}")
    if limit is not None:
        samples = samples[:limit]

    started = time.perf_counter()
    predictions = tuple(
        predictions_from_detections(detector.predict(sample.image_path))
        for sample in samples
    )
    duration = time.perf_counter() - started

    evaluation = build_evaluation(
        samples,
        predictions,
        names,
        model_id="solder-defect",
        model_name=getattr(detector, "name", settings.defect_model_name),
        engine=detector.engine,
        split=split,
        dataset=str(dataset_dir),
        conf_threshold=getattr(detector, "conf", settings.conf_threshold),
        class_thresholds_applied=bool(getattr(detector, "thresholds_applied", False)),
        imgsz=int(getattr(detector, "imgsz", settings.detector_imgsz)),
        tiling_enabled=settings.tiling_enabled,
        device=settings.device,
        duration_seconds=duration,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{evaluation.model_id}-{split}.json"
    output_path.write_text(
        json.dumps(evaluation.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    score = evaluation.overall
    print(
        f"{evaluation.image_count} görsel, {evaluation.ground_truth_boxes} kutu: "
        f"precision {score.precision:.4f}, recall {score.recall:.4f}, "
        f"F1 {score.f1:.4f}, mAP50 {score.ap50:.4f}, "
        f"mAP50-95 {score.ap50_95:.4f}, "
        f"{evaluation.mean_inference_ms:.1f} ms/görsel"
    )
    if evaluation.classes_without_ground_truth:
        print(
            "Test split'inde ground truth bulunmayan sınıflar (mAP dışında): "
            + ", ".join(evaluation.classes_without_ground_truth)
        )
    print(f"Sonuç: {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="test", help="veri seti split'i (varsayılan: test)")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=settings.evaluation_dataset_dir,
        help="final_solder klasörü",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.evaluation_output_dir,
        help="JSON çıktı klasörü",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="yalnızca ilk N görsel (hızlı kontrol)"
    )
    args = parser.parse_args()

    evaluate(_resolve(args.dataset_dir), args.split, _resolve(args.output_dir), args.limit)


if __name__ == "__main__":
    main()
