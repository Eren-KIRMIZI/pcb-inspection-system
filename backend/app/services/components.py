from pathlib import Path

from ..config import BASE_DIR, settings
from ..schemas import Detection


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BASE_DIR / path


class ComponentDetector:
    """Hazır 13 sınıflı YOLO modeliyle komponent konumu/türü üretir."""

    def __init__(self, model_path: Path, conf: float, imgsz: int, device: str) -> None:
        from ultralytics import YOLO

        self.model = YOLO(str(model_path))
        self.conf = conf
        self.imgsz = imgsz
        self.device = device

    def predict(self, image_path: Path) -> list[Detection]:
        results = self.model.predict(
            source=str(image_path),
            conf=self.conf,
            imgsz=self.imgsz,
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


_detector: ComponentDetector | None = None


def get_component_detector() -> ComponentDetector | None:
    global _detector
    if settings.component_model_path is None:
        return None
    if _detector is None:
        _detector = ComponentDetector(
            _resolve(settings.component_model_path),
            settings.component_conf_threshold,
            settings.component_imgsz,
            settings.device,
        )
    return _detector
