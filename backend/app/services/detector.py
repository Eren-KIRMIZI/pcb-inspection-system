from pathlib import Path
from typing import Protocol

from ..config import settings
from ..schemas import Detection


class Detector(Protocol):
    def predict(self, image_path: Path) -> list[Detection]: ...


class MockDetector:
    """Model ağırlığı yokken uçtan uca akışı test etmek için boş sonuç döner."""

    def predict(self, image_path: Path) -> list[Detection]:
        return []


class YoloDetector:
    def __init__(self, model_path: Path, conf: float, device: str) -> None:
        from ultralytics import YOLO

        self.model = YOLO(str(model_path))
        self.conf = conf
        self.device = device

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
                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=self.model.names.get(class_id, str(class_id)),
                        confidence=float(box.conf[0]),
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
                settings.model_path,
                settings.conf_threshold,
                settings.device,
            )
    return _detector
