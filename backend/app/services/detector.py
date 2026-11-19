import json
from pathlib import Path
from typing import Protocol

from ..config import BASE_DIR, settings
from ..schemas import Detection


class Detector(Protocol):
    def predict(self, image_path: Path) -> list[Detection]: ...


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BASE_DIR / path


class MockDetector:
    """Model ağırlığı yokken uçtan uca akışı test etmek için boş sonuç döner."""

    def predict(self, image_path: Path) -> list[Detection]:
        return []


class YoloDetector:
    def __init__(
        self,
        model_path: Path,
        conf: float,
        device: str,
        thresholds_path: Path | None = None,
    ) -> None:
        from ultralytics import YOLO

        self.model = YOLO(str(model_path))
        self.conf = conf
        self.device = device
        self.thresholds: dict[str, float] = {}

        if thresholds_path is not None:
            path = _resolve(thresholds_path)
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self.conf = float(raw.get("global", self.conf))
                    for key in ("thresholds", "per_class"):
                        nested = raw.get(key)
                        if isinstance(nested, dict):
                            raw = nested
                            break
                self.thresholds = {
                    str(key): float(value)
                    for key, value in raw.items()
                    if isinstance(value, (int, float))
                }

    def predict(self, image_path: Path) -> list[Detection]:
        results = self.model.predict(
            source=str(image_path),
            conf=self.conf,
            device=self.device,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = self.model.names.get(class_id, str(class_id))
                confidence = float(box.conf[0])
                threshold = self.thresholds.get(class_name, self.conf)
                if confidence < threshold:
                    continue
                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=confidence,
                        bbox=[float(value) for value in box.xyxy[0]],
                    )
                )
        return detections


_detector: Detector | None = None


def get_detector() -> Detector:
    global _detector
    if _detector is None:
        if settings.use_mock_detector or settings.model_path is None:
            _detector = MockDetector()
        else:
            _detector = YoloDetector(
                _resolve(settings.model_path),
                settings.conf_threshold,
                settings.device,
                settings.thresholds_path,
            )
    return _detector
