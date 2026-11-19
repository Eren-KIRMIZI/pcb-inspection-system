import json
import math
import re
from pathlib import Path

import cv2
import numpy as np

from ..config import BASE_DIR, settings
from ..schemas import Detection, ReferenceBoard, ReferenceCheck, ReferenceIssue
from .alignment import align_images
from .components import get_component_detector

TYPE_ALIASES = {
    "r": "resistor",
    "c": "capacitor",
    "u": "ic",
    "d": "diode",
    "l": "inductor",
    "j": "connector",
    "q": "transistor",
    "y": "oscillator",
    "sw": "switch/button",
    "led": "led",
}


def _safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Geçersiz referans adı")
    return name


def reference_path(name: str) -> Path:
    return settings.data_dir / "references" / f"{_safe_name(name)}.json"


def save_reference(board: ReferenceBoard) -> Path:
    path = reference_path(board.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(board.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_reference(name: str) -> ReferenceBoard | None:
    try:
        path = reference_path(name)
    except ValueError:
        return None
    if not path.exists():
        return None
    return ReferenceBoard.model_validate_json(path.read_text(encoding="utf-8"))


def _normalize_type(value: str) -> str:
    normalized = value.strip().lower()
    return TYPE_ALIASES.get(normalized, normalized)


def _center(detection: Detection) -> tuple[float, float]:
    x1, y1, x2, y2 = detection.bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _map_point(
    x: float,
    y: float,
    reference_size: tuple[int, int],
    target_size: tuple[int, int],
    matrix: np.ndarray | None,
) -> tuple[float, float]:
    ref_w, ref_h = reference_size
    target_w, target_h = target_size
    point = np.float32([[[x * ref_w, y * ref_h]]])
    if matrix is not None:
        mapped = cv2.perspectiveTransform(point, matrix)[0][0]
        return float(mapped[0]), float(mapped[1])
    return x * target_w, y * target_h


def compare_board(
    reference: ReferenceBoard,
    target_path: Path,
    detections: list[Detection] | None = None,
) -> ReferenceCheck:
    """Beklenen komponentleri tespit edilenlerle karşılaştırır."""

    reference_image = cv2.imread(str(BASE_DIR / reference.image_path))
    target_image = cv2.imread(str(target_path))
    if reference_image is None or target_image is None:
        raise ValueError("Referans veya test görüntüsü okunamadı")

    ref_h, ref_w = reference_image.shape[:2]
    target_h, target_w = target_image.shape[:2]
    matrix = align_images(BASE_DIR / reference.image_path, target_path)

    if detections is None:
        detector = get_component_detector()
        detections = detector.predict(target_path) if detector else []

    match_distance = max(12.0, target_w * settings.reference_match_distance_ratio)
    shift_distance = max(10.0, target_w * settings.reference_shift_distance_ratio)

    issues: list[ReferenceIssue] = []
    for component in reference.components:
        point = _map_point(
            component.x,
            component.y,
            (ref_w, ref_h),
            (target_w, target_h),
            matrix,
        )
        candidates: list[tuple[float, Detection]] = []
        for detection in detections:
            center = _center(detection)
            distance = math.hypot(center[0] - point[0], center[1] - point[1])
            candidates.append((distance, detection))

        expected_type = _normalize_type(component.type)
        same_type = [
            (distance, detection)
            for distance, detection in candidates
            if _normalize_type(detection.class_name) == expected_type
        ]
        if same_type:
            distance, detection = min(same_type, key=lambda item: item[0])
            if distance > shift_distance:
                issues.append(
                    ReferenceIssue(
                        ref=component.ref,
                        expected_type=component.type,
                        issue="shifted_component",
                        distance_px=round(distance, 1),
                        detected_type=detection.class_name,
                        confidence=detection.confidence,
                    )
                )
            continue

        nearby = [
            (distance, detection)
            for distance, detection in candidates
            if distance <= match_distance
        ]
        if nearby:
            distance, detection = min(nearby, key=lambda item: item[0])
            issues.append(
                ReferenceIssue(
                    ref=component.ref,
                    expected_type=component.type,
                    issue="wrong_component",
                    distance_px=round(distance, 1),
                    detected_type=detection.class_name,
                    confidence=detection.confidence,
                )
            )
        else:
            issues.append(
                ReferenceIssue(
                    ref=component.ref,
                    expected_type=component.type,
                    issue="missing_component",
                )
            )

    return ReferenceCheck(
        reference=reference.name,
        aligned=matrix is not None,
        expected_count=len(reference.components),
        detected_count=len(detections),
        issues=issues,
    )
