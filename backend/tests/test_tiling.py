"""AOI Engine 2.0 / adım 20: tiling, koordinat map'i ve NMS."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.app.config import settings
from backend.app.schemas import Detection
from backend.app.services.detector import YoloDetector
from backend.app.services.tiling import Tile, generate_tiles, iou, map_bbox, nms_detections


class _Box:
    def __init__(self, class_id: int, confidence: float, xyxy: list[float]) -> None:
        self.cls = [class_id]
        self.conf = [confidence]
        self.xyxy = [xyxy]


class _Result:
    def __init__(self, boxes: list[_Box]) -> None:
        self.boxes = boxes


class _FakeModel:
    names = {0: "resistor"}

    def __init__(self, boxes: list[_Box]) -> None:
        self._boxes = boxes
        self.calls: list[tuple[object, int]] = []

    def predict(
        self, source: object, conf: float, imgsz: int, device: str, verbose: bool
    ) -> list[_Result]:
        self.calls.append((source, imgsz))
        return [_Result(self._boxes)]


def _detection(name: str, bbox: list[float], confidence: float) -> Detection:
    return Detection(class_id=0, class_name=name, confidence=confidence, bbox=bbox)


def _fake_detector(model: _FakeModel, thresholds: dict[str, float] | None = None) -> YoloDetector:
    detector = YoloDetector.__new__(YoloDetector)
    detector.model = model
    detector.conf = 0.2
    detector.thresholds = thresholds or {}
    detector.device = "cpu"
    detector.imgsz = settings.detector_imgsz
    detector.name = "fake-model.pt"
    detector.engine = "real"
    detector.thresholds_applied = bool(thresholds)
    return detector


def test_generate_tiles_without_overlap() -> None:
    assert generate_tiles(200, 150, 100, 0.0) == (
        Tile(0, 0, 100, 100),
        Tile(100, 0, 200, 100),
        Tile(0, 100, 100, 150),
        Tile(100, 100, 200, 150),
    )


def test_generate_tiles_with_overlap() -> None:
    tiles = generate_tiles(250, 250, 100, 0.2)
    assert len(tiles) == 9
    assert Tile(80, 0, 180, 100) in tiles
    assert all(tile.x2 <= 250 and tile.y2 <= 250 for tile in tiles)
    assert generate_tiles(0, 100, 64, 0.2) == ()


def test_map_bbox_shifts_to_full_image_coordinates() -> None:
    assert map_bbox([10.0, 20.0, 30.0, 40.0], Tile(100, 200, 300, 400)) == [
        110.0,
        220.0,
        130.0,
        240.0,
    ]


def test_iou_values() -> None:
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == pytest.approx(1.0)
    assert iou([0, 0, 10, 10], [10, 0, 20, 10]) == 0.0
    assert iou([0, 0, 10, 10], [5, 0, 15, 10]) == pytest.approx(1 / 3)


def test_nms_keeps_higher_confidence_and_other_classes() -> None:
    items = [
        _detection("resistor", [0, 0, 10, 10], 0.7),
        _detection("resistor", [1, 1, 11, 11], 0.9),
        _detection("capacitor", [2, 2, 12, 12], 0.6),
    ]

    result = nms_detections(items, 0.3)

    assert len(result) == 2
    assert result[0].class_name == "resistor"
    assert result[0].confidence == 0.9
    assert result[1].class_name == "capacitor"


def test_tiling_maps_coordinates_and_passes_imgsz(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "tiling_enabled", True)
    monkeypatch.setattr(settings, "tile_size", 100)
    monkeypatch.setattr(settings, "tile_overlap", 0.0)
    monkeypatch.setattr(settings, "tile_nms_iou", 0.45)
    monkeypatch.setattr(settings, "detector_imgsz", 640)

    image_path = tmp_path / "board.jpg"
    cv2.imwrite(str(image_path), 255 * np.ones((200, 200, 3), dtype=np.uint8))
    model = _FakeModel([_Box(0, 0.9, [10.0, 10.0, 30.0, 30.0])])
    detector = _fake_detector(model)

    detections = detector.predict(image_path)

    assert len(detections) == 4
    assert {tuple(item.bbox) for item in detections} == {
        (10.0, 10.0, 30.0, 30.0),
        (110.0, 10.0, 130.0, 30.0),
        (10.0, 110.0, 30.0, 130.0),
        (110.0, 110.0, 130.0, 130.0),
    }
    assert len(model.calls) == 4
    assert all(imgsz == 640 for _, imgsz in model.calls)


def test_class_thresholds_still_apply_in_tiling(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "tiling_enabled", True)
    monkeypatch.setattr(settings, "tile_size", 100)
    monkeypatch.setattr(settings, "tile_overlap", 0.0)

    image_path = tmp_path / "board.jpg"
    cv2.imwrite(str(image_path), 255 * np.ones((120, 120, 3), dtype=np.uint8))
    model = _FakeModel([_Box(0, 0.9, [10.0, 10.0, 30.0, 30.0])])
    detector = _fake_detector(model, thresholds={"resistor": 0.95})

    assert detector.predict(image_path) == []


def test_full_image_mode_uses_single_prediction(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "tiling_enabled", False)

    image_path = tmp_path / "board.jpg"
    cv2.imwrite(str(image_path), 255 * np.ones((200, 200, 3), dtype=np.uint8))
    model = _FakeModel([_Box(0, 0.9, [10.0, 10.0, 30.0, 30.0])])
    detector = _fake_detector(model)

    detections = detector.predict(image_path)

    assert len(detections) == 1
    assert len(model.calls) == 1
    assert isinstance(model.calls[0][0], str)
