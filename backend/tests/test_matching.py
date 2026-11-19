"""AOI Engine 2.0 / adım 17: global komponent eşleştirme (Hungarian)."""

from pathlib import Path

import cv2
import numpy as np

from backend.app.config import settings
from backend.app.schemas import Detection, ReferenceBoard, ReferenceComponent
from backend.app.services.matching import (
    build_cost_matrix,
    match_components,
)
from backend.app.services.reference import compare_board


def _detection(
    class_name: str,
    center: tuple[float, float],
    confidence: float = 1.0,
    size: float = 10.0,
) -> Detection:
    cx, cy = center
    return Detection(
        class_id=0,
        class_name=class_name,
        confidence=confidence,
        bbox=[cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2],
    )


def _cost(
    expected: str,
    detected: str,
    confidence: float = 1.0,
    size: float = 10.0,
    distance: float = 0.0,
    match_distance: float = 12.0,
) -> float:
    points = [(0.0, 0.0)]
    centers = [(distance, 0.0)]
    detections = [_detection(detected, centers[0], confidence, size)]
    costs = build_cost_matrix(
        points,
        centers,
        detections,
        [expected.lower()],
        [detected.lower()],
        match_distance,
    )
    return float(costs[0, 0])


def test_exact_match_has_zero_cost() -> None:
    cost = _cost("resistor", "Resistor")
    assert cost == 0.0


def test_type_mismatch_adds_penalty() -> None:
    cost = _cost("resistor", "Capacitor")
    assert cost == settings.matching_type_penalty


def test_low_confidence_adds_cost() -> None:
    cost = _cost("resistor", "resistor", confidence=0.5)
    expected = 0.5 * settings.matching_confidence_weight
    assert abs(cost - expected) < 1e-6


def test_outlier_area_adds_capped_cost() -> None:
    # Tek tespitte medyan o tespitin kendisidir; sapma için en az üç tespit gerekir.
    centers = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
    detections = [
        _detection("resistor", centers[0], size=10.0),
        _detection("resistor", centers[1], size=10.0),
        _detection("resistor", centers[2], size=100.0),
    ]
    costs = build_cost_matrix(
        [(0.0, 0.0)],
        centers,
        detections,
        ["resistor"],
        ["resistor"] * 3,
        12.0,
    )

    area_penalty = settings.matching_area_cap * settings.matching_area_weight
    expected = 2.0 / 12.0 + area_penalty
    assert abs(float(costs[0, 2]) - expected) < 1e-6


def test_distance_is_normalized_and_capped() -> None:
    cost = _cost("resistor", "resistor", distance=6.0, match_distance=12.0)
    assert abs(cost - 0.5) < 1e-6

    outside = _cost("resistor", "resistor", distance=13.0, match_distance=12.0)
    assert outside >= settings.matching_invalid_cost


def test_hungarian_finds_global_optimum_not_greedy() -> None:
    # Açgözlü R1→D1 (1.0), R2→D2 (6.0) = 7.0 seçer; optimum 2.0 + 1.5 = 3.5.
    costs = np.array([[1.0, 2.0], [1.5, 6.0]])
    points = [(0.0, 0.0), (10.0, 0.0)]
    centers = [(0.0, 0.0), (10.0, 0.0)]

    matching = match_components(
        costs, points, centers, ["resistor", "resistor"], ["resistor", "resistor"], 12.0
    )

    pairs = [(item.component_index, item.detection_index) for item in matching.assignments]
    assert pairs == [(0, 1), (1, 0)]
    assert matching.cost_total == 3.5
    assert matching.unmatched_components == ()
    assert matching.unmatched_detections == ()
    assert matching.cost_mean == 1.75


def test_invalid_assignments_are_not_counted() -> None:
    costs = np.array(
        [
            [settings.matching_invalid_cost, settings.matching_invalid_cost],
            [0.5, settings.matching_invalid_cost],
        ]
    )
    points = [(0.0, 0.0), (1.0, 0.0)]
    centers = [(0.0, 0.0), (2.0, 0.0)]

    matching = match_components(
        costs, points, centers, ["ic", "r"], ["ic", "r"], 12.0
    )

    assert [(item.component_index, item.detection_index) for item in matching.assignments] == [
        (1, 0)
    ]
    assert matching.unmatched_components == (0,)
    assert matching.unmatched_detections == (1,)


def test_compare_board_uses_hungarian_matching(tmp_path: Path) -> None:
    image = tmp_path / "board.jpg"
    cv2.imwrite(str(image), 255 * np.ones((100, 100, 3), dtype=np.uint8))
    board = ReferenceBoard(
        name="matching-test",
        image_path=str(image),
        components=[
            ReferenceComponent(ref="R1", type="resistor", x=0.3, y=0.5),
            ReferenceComponent(ref="R2", type="capacitor", x=0.7, y=0.5),
        ],
    )
    detections = [
        _detection("resistor", (31.0, 50.0)),
        _detection("capacitor", (70.0, 50.0)),
    ]

    check = compare_board(board, image, detections)

    assert check.matched_count == 2
    assert check.issues == []
    assert check.matching is not None
    assert check.matching.algorithm == "hungarian"
    assert check.matching.assignments == 2
    assert check.matching.unmatched_components == 0
    assert check.matching.unmatched_detections == 0
    assert check.matching.cost_total >= 0.0
