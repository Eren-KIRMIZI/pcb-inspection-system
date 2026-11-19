import re
from pathlib import Path

import cv2
import numpy as np

from ..config import BASE_DIR, settings
from ..errors import ImageReadError
from ..schemas import (
    AlignmentInfo,
    Detection,
    MatchingInfo,
    ReferenceBoard,
    ReferenceCheck,
    ReferenceIssue,
)
from .alignment import align_images
from .components import get_component_detector
from .matching import build_cost_matrix, match_components

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
    """Beklenen komponentleri tekil eşleştirmeyle karşılaştırır.

    Ham YOLO tespit sayısı komponent sayısı olarak kullanılmaz: yalnızca güven eşiğini
    geçen tespitler eşleştirmeye katılır ve her tespit en fazla bir BOM satırına atanır.
    """

    reference_image_path = BASE_DIR / reference.image_path
    reference_image = cv2.imread(str(reference_image_path))
    target_image = cv2.imread(str(target_path))
    if reference_image is None or target_image is None:
        raise ImageReadError("Referans veya test görüntüsü okunamadı")

    ref_h, ref_w = reference_image.shape[:2]
    target_h, target_w = target_image.shape[:2]
    alignment = align_images(reference_image_path, target_path)
    matrix = alignment.matrix if alignment.ok else None
    alignment_info = AlignmentInfo(
        trusted=alignment.ok,
        inlier_count=alignment.inlier_count,
        inlier_ratio=alignment.inlier_ratio,
        scale=alignment.scale,
        rotation_deg=alignment.rotation_deg,
        reason=alignment.reason,
    )

    if detections is None:
        detector = get_component_detector()
        detections = detector.predict(target_path) if detector else []

    qualified = [
        detection
        for detection in detections
        if detection.confidence >= settings.reference_component_min_confidence
    ]
    components = sorted(reference.components, key=lambda item: item.ref)
    centers = [_center(detection) for detection in qualified]
    points = [
        _map_point(
            component.x,
            component.y,
            (ref_w, ref_h),
            (target_w, target_h),
            matrix,
        )
        for component in components
    ]
    expected_types = [_normalize_type(component.type) for component in components]
    detected_types = [
        _normalize_type(detection.class_name) for detection in qualified
    ]

    match_distance = max(12.0, target_w * settings.reference_match_distance_ratio)
    shift_distance = max(10.0, target_w * settings.reference_shift_distance_ratio)

    # D3: BOM sırasına göre açgözlü eşleştirme yerine global minimum maliyetli
    # bire-bir atama (Hungarian). Maliyet mesafe/tip/güven/alan bileşenlerinden
    # oluşur; eşik dışı çiftler atanamaz ve "missing"/"extra" olarak kalır.
    costs = build_cost_matrix(
        points, centers, qualified, expected_types, detected_types, match_distance
    )
    matching = match_components(
        costs, points, centers, expected_types, detected_types, match_distance
    )

    issues: list[ReferenceIssue] = []
    matched_count = 0

    for assignment in matching.assignments:
        component = components[assignment.component_index]
        detection = qualified[assignment.detection_index]
        if assignment.type_matched:
            matched_count += 1
            if assignment.distance > shift_distance:
                issues.append(
                    ReferenceIssue(
                        ref=component.ref,
                        expected_type=component.type,
                        issue="shifted_component",
                        distance_px=round(assignment.distance, 1),
                        detected_type=detection.class_name,
                        confidence=detection.confidence,
                    )
                )
        else:
            issues.append(
                ReferenceIssue(
                    ref=component.ref,
                    expected_type=component.type,
                    issue="wrong_component",
                    distance_px=round(assignment.distance, 1),
                    detected_type=detection.class_name,
                    confidence=detection.confidence,
                )
            )

    for index in matching.unmatched_components:
        component = components[index]
        issues.append(
            ReferenceIssue(
                ref=component.ref,
                expected_type=component.type,
                issue="missing_component",
            )
        )

    for index in matching.unmatched_detections:
        detection = qualified[index]
        cx, cy = centers[index]
        issues.append(
            ReferenceIssue(
                # Adım 18'de anlamlı bir atama kimliği üretilecek; şimdilik
                # mevcut şema korunuyor (D3 kapsamı yalnızca global atama).
                ref="—",
                expected_type="—",
                issue="extra_component",
                detected_type=detection.class_name,
                confidence=detection.confidence,
                x=round(cx / target_w, 4),
                y=round(cy / target_h, 4),
            )
        )

    def count(issue_type: str) -> int:
        return sum(1 for issue in issues if issue.issue == issue_type)

    return ReferenceCheck(
        reference=reference.name,
        aligned=alignment.ok,
        alignment=alignment_info,
        expected_count=len(reference.components),
        raw_component_detections=len(detections),
        qualified_component_detections=len(qualified),
        matched_count=matched_count,
        missing_count=count("missing_component"),
        wrong_count=count("wrong_component"),
        shifted_count=count("shifted_component"),
        extra_count=count("extra_component"),
        issues=issues,
        matching=MatchingInfo(
            algorithm="hungarian",
            cost_total=matching.cost_total,
            cost_mean=round(matching.cost_mean, 4)
            if matching.cost_mean is not None
            else None,
            assignments=len(matching.assignments),
            unmatched_components=len(matching.unmatched_components),
            unmatched_detections=len(matching.unmatched_detections),
        ),
    )
