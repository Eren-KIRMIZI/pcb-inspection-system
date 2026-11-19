from pathlib import Path

import cv2
import numpy as np

from backend.app.schemas import Detection, ReferenceBoard, ReferenceComponent
from backend.app.services.reference import compare_board


def _image(tmp_path: Path) -> Path:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 255 * np.ones((100, 100, 3), dtype="uint8"))
    return image


def _board(image_path: Path, components: list[ReferenceComponent] | None = None) -> ReferenceBoard:
    return ReferenceBoard(
        name="test",
        image_path=str(image_path),
        components=components
        or [ReferenceComponent(ref="R1", type="resistor", x=0.5, y=0.5)],
    )


def _detection(name: str, center: float, confidence: float = 0.9) -> Detection:
    return Detection(
        class_id=0,
        class_name=name,
        confidence=confidence,
        bbox=[center - 5, center - 5, center + 5, center + 5],
    )


def test_matching_component_has_no_issue(tmp_path: Path) -> None:
    image = _image(tmp_path)
    check = compare_board(_board(image), image, [_detection("Resistor", 50)])
    assert check.issues == []
    assert check.matched_count == 1
    assert check.extra_count == 0


def test_wrong_type_is_reported(tmp_path: Path) -> None:
    image = _image(tmp_path)
    check = compare_board(_board(image), image, [_detection("Capacitor", 50)])
    assert check.issues[0].issue == "wrong_component"
    assert check.issues[0].detected_type == "Capacitor"
    assert check.wrong_count == 1


def test_missing_component_is_reported(tmp_path: Path) -> None:
    image = _image(tmp_path)
    check = compare_board(_board(image), image, [])
    assert check.issues[0].issue == "missing_component"
    assert check.missing_count == 1


def test_shifted_component_is_reported(tmp_path: Path) -> None:
    image = _image(tmp_path)
    shifted = Detection(
        class_id=0,
        class_name="Resistor",
        confidence=0.9,
        bbox=[56.0, 45.0, 66.0, 55.0],  # merkez (61, 50): 11 px yatay kayma
    )
    check = compare_board(_board(image), image, [shifted])
    assert check.issues[0].issue == "shifted_component"
    assert check.issues[0].distance_px == 11.0


def test_extra_component_is_reported(tmp_path: Path) -> None:
    image = _image(tmp_path)
    check = compare_board(
        _board(image),
        image,
        [_detection("Resistor", 50), _detection("Capacitor", 95)],
    )
    assert check.extra_count == 1
    assert check.issues[0].issue == "extra_component"
    assert check.issues[0].detected_type == "Capacitor"


def test_low_confidence_detection_is_ignored(tmp_path: Path) -> None:
    image = _image(tmp_path)
    check = compare_board(_board(image), image, [_detection("Resistor", 50, 0.2)])
    assert check.raw_component_detections == 1
    assert check.qualified_component_detections == 0
    assert check.issues[0].issue == "missing_component"


def test_one_detection_matches_only_one_reference_row(tmp_path: Path) -> None:
    image = _image(tmp_path)
    components = [
        ReferenceComponent(ref="R1", type="resistor", x=0.5, y=0.5),
        ReferenceComponent(ref="R2", type="resistor", x=0.5, y=0.5),
    ]
    check = compare_board(_board(image, components), image, [_detection("Resistor", 50)])
    assert check.matched_count == 1
    assert check.missing_count == 1
    assert check.extra_count == 0


def test_counts_are_consistent(tmp_path: Path) -> None:
    image = _image(tmp_path)
    check = compare_board(
        _board(image),
        image,
        [_detection("Capacitor", 50), _detection("Resistor", 90)],
    )
    assert check.matched_count + check.missing_count + check.wrong_count + check.shifted_count == check.expected_count
    assert check.extra_count == check.qualified_component_detections - check.matched_count - check.wrong_count
