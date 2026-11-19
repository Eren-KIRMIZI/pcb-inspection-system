import json
import threading
from pathlib import Path
from typing import Protocol

import cv2

from ..config import BASE_DIR, settings
from ..errors import ModelUnavailableError
from ..schemas import Detection, EngineMode
from .tiling import generate_tiles, map_bbox, nms_detections


class Detector(Protocol):
    engine: EngineMode
    name: str
    thresholds_applied: bool

    def predict(self, image_path: Path) -> list[Detection]: ...


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BASE_DIR / path


class MockDetector:
    """Model ağırlığı yokken akışı test etmek için boş sonuç döner."""

    engine: EngineMode = "mock"
    name: str = "mock-detector"
    thresholds_applied: bool = False

    def predict(self, image_path: Path) -> list[Detection]:
        return []


class YoloDetector:
    engine: EngineMode = "real"
    thresholds_applied: bool = False

    def __init__(
        self,
        model_path: Path,
        conf: float,
        device: str,
        thresholds_path: Path | None = None,
        imgsz: int = 640,
    ) -> None:
        if not model_path.exists():
            raise ModelUnavailableError(f"Model dosyası bulunamadı: {model_path}")

        from ultralytics import YOLO

        self.model = YOLO(str(model_path))
        self.name = model_path.name
        self.conf = conf
        self.device = device
        self.imgsz = imgsz
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
                    self.thresholds_applied = bool(self.thresholds)

    def _to_detection(
        self, box: object, offset: tuple[float, float] = (0.0, 0.0)
    ) -> Detection | None:
        """YOLO kutusunu sınıf eşiği kontrolünden sonra ``Detection`` yapar.

        Sınıf eşikleri ``thresholds.json`` değerlerinden gelir; tile modunda da
        aynı eşikler uygulanır (D5 gereksinimi).
        """

        class_id = int(box.cls[0])  # type: ignore[attr-defined]
        class_name = self.model.names.get(class_id, str(class_id))
        confidence = float(box.conf[0])  # type: ignore[attr-defined]
        threshold = self.thresholds.get(class_name, self.conf)
        if confidence < threshold:
            return None
        bbox = [float(value) for value in box.xyxy[0]]  # type: ignore[attr-defined]
        ox, oy = offset
        return Detection(
            class_id=class_id,
            class_name=class_name,
            confidence=confidence,
            bbox=[bbox[0] + ox, bbox[1] + oy, bbox[2] + ox, bbox[3] + oy],
        )

    def _detect(
        self, source: object, offset: tuple[float, float] = (0.0, 0.0)
    ) -> list[Detection]:
        results = self.model.predict(
            source=source,
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
                detection = self._to_detection(box, offset)
                if detection is not None:
                    detections.append(detection)
        return detections

    def predict(self, image_path: Path) -> list[Detection]:
        """Tiling kapalıysa tam görseli, açıksa örtüşen tile'ları çıkarır."""

        if not settings.tiling_enabled:
            return self._detect(str(image_path))

        image = cv2.imread(str(image_path))
        if image is None:
            return []
        height, width = image.shape[:2]
        detections: list[Detection] = []
        for tile in generate_tiles(
            width, height, settings.tile_size, settings.tile_overlap
        ):
            crop = image[tile.y1 : tile.y2, tile.x1 : tile.x2]
            detections.extend(
                self._detect(crop, (float(tile.x1), float(tile.y1)))
            )
        return nms_detections(detections, settings.tile_nms_iou)


_detector: Detector | None = None
_detector_lock = threading.Lock()


def is_detector_loaded() -> bool:
    """Modelin bu süreçte yüklenip yüklenmediğini belirtir; yükleme tetiklemez."""

    return _detector is not None


def get_detector() -> Detector:
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                if settings.use_mock_detector or settings.model_path is None:
                    _detector = MockDetector()
                else:
                    _detector = YoloDetector(
                        _resolve(settings.model_path),
                        settings.conf_threshold,
                        settings.device,
                        settings.thresholds_path,
                        settings.detector_imgsz,
                    )
    return _detector
