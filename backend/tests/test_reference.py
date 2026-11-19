from pathlib import Path

import cv2
import numpy as np

from backend.app.schemas import Detection, ReferenceBoard, ReferenceComponent
from backend.app.services.reference import compare_board


def _board(image_path: Path) -> ReferenceBoard:
    return ReferenceBoard(
        name="test",
        image_path=str(image_path),
        components=[ReferenceComponent(ref="R1", type="resistor", x=0.5, y=0.5)],
    )


def _detection(name: str, center: float) -> Detection:
    return Detection(
        class_id=0,
        class_name=name,
        confidence=0.9,
        bbox=[center - 5, center - 5, center + 5, center + 5],
    )


def test_matching_component_has_no_issue(tmp_path: Path) -> None:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 255 * np.ones((100, 100, 3), dtype="uint8"))
    check = compare_board(_board(image), image, [_detection("Resistor", 50)])
    assert check.issues == []


def test_wrong_type_is_reported(tmp_path: Path) -> None:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 255 * np.ones((100, 100, 3), dtype="uint8"))
    check = compare_board(_board(image), image, [_detection("Capacitor", 50)])
    assert check.issues[0].issue == "wrong_component"
    assert check.issues[0].detected_type == "Capacitor"


def test_missing_component_is_reported(tmp_path: Path) -> None:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 255 * np.ones((100, 100, 3), dtype="uint8"))
    check = compare_board(_board(image), image, [])
    assert check.issues[0].issue == "missing_component"


def test_shifted_component_is_reported(tmp_path: Path) -> None:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 255 * np.ones((100, 100, 3), dtype="uint8"))
    check = compare_board(_board(image), image, [_detection("Resistor", 80)])
    assert check.issues[0].issue == "shifted_component"
