"""AOI Engine 2.0 / adım 17: global komponent eşleştirme.

BOM sırasına göre açgözlü en yakın komşu, iki referans aynı tespit için
yarıştığında global optimumu kaçırır. Bu modül scipy ``linear_sum_assignment``
(Hungarian) ile minimum maliyetli bire-bir atama yapar.

Maliyet bileşenleri:

* **mesafe** — hizalanmış referans noktası ile tespit merkezi arası,
  ``match_distance`` değerine normalize edilir (0..1).
* **tip** — beklenen ve tespit edilen tip uyuşmazlığında sabit ceza.
* **güven** — düşük güvenli tespitler cezalandırılır.
* **alan** — tespit bbox alanının, aynı görseldeki tespitlerin alan medyanından
  sapması; aykırı boyutlu kutular gürültü olabilir.

Eşik dışı (``match_distance`` ötesi) çiftler ``matching_invalid_cost`` ile
işaretlenir; atanamazlar. ``ReferenceCheck`` alanları değiştirilmez, yalnızca
maliyet özeti eklenir.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..config import settings
from ..schemas import Detection


@dataclass(frozen=True)
class MatchAssignment:
    component_index: int
    detection_index: int
    cost: float
    distance: float
    type_matched: bool


@dataclass(frozen=True)
class MatchingResult:
    assignments: tuple[MatchAssignment, ...]
    unmatched_components: tuple[int, ...]
    unmatched_detections: tuple[int, ...]
    cost_total: float

    @property
    def cost_mean(self) -> float | None:
        return self.cost_total / len(self.assignments) if self.assignments else None


def _area(detection: Detection) -> float:
    x1, y1, x2, y2 = detection.bbox
    return max(0.0, (x2 - x1) * (y2 - y1))


def build_cost_matrix(
    points: list[tuple[float, float]],
    centers: list[tuple[float, float]],
    detections: list[Detection],
    expected_types: list[str],
    detected_types: list[str],
    match_distance: float,
) -> np.ndarray:
    """``N`` referans x ``M`` tespit maliyet matrisi üretir.

    ``points`` hizalanmış referans koordinatları, ``centers`` tespit merkezleridir.
    Tipler normalize edilmiş olarak geçilir (örn. ``ic``, ``resistor``).
    """

    count_ref, count_det = len(points), len(centers)
    if len(detections) != count_det or len(expected_types) != count_ref:
        raise ValueError("Eşleştirme girdilerinin uzunlukları tutarlı değil")

    costs = np.full(
        (count_ref, count_det), settings.matching_invalid_cost, dtype=float
    )
    if count_ref == 0 or count_det == 0:
        return costs

    areas = [_area(detection) for detection in detections]
    median_area = float(np.median(areas)) if areas else 0.0

    for i, (px, py) in enumerate(points):
        for j, (cx, cy) in enumerate(centers):
            distance = float(np.hypot(cx - px, cy - py))
            if distance > match_distance:
                continue
            cost = distance / max(match_distance, 1e-6)
            if detected_types[j] != expected_types[i]:
                cost += settings.matching_type_penalty
            cost += (1.0 - detections[j].confidence) * settings.matching_confidence_weight
            if median_area > 0.0 and areas[j] > 0.0:
                ratio = max(areas[j] / median_area, median_area / areas[j])
                cost += (
                    min(ratio - 1.0, settings.matching_area_cap)
                    * settings.matching_area_weight
                )
            costs[i, j] = cost
    return costs


def match_components(
    costs: np.ndarray,
    points: list[tuple[float, float]],
    centers: list[tuple[float, float]],
    expected_types: list[str],
    detected_types: list[str],
    match_distance: float,
) -> MatchingResult:
    """Hungarian ile minimum maliyetli bire-bir atama yapar."""

    count_ref, count_det = costs.shape
    if len(expected_types) != count_ref or len(detected_types) != count_det:
        raise ValueError("Tip listeleri maliyet matrisiyle uyumlu değil")
    if count_ref == 0 or count_det == 0:
        return MatchingResult(
            assignments=(),
            unmatched_components=tuple(range(count_ref)),
            unmatched_detections=tuple(range(count_det)),
            cost_total=0.0,
        )

    row_ind, col_ind = linear_sum_assignment(costs)
    assignments: list[MatchAssignment] = []
    for i, j in zip(row_ind, col_ind):
        cost = float(costs[i, j])
        if cost >= settings.matching_invalid_cost:
            continue
        px, py = points[i]
        cx, cy = centers[j]
        type_matched = detected_types[j] == expected_types[i]
        assignments.append(
            MatchAssignment(
                component_index=int(i),
                detection_index=int(j),
                cost=cost,
                distance=float(np.hypot(cx - px, cy - py)),
                type_matched=type_matched,
            )
        )

    assigned_components = {item.component_index for item in assignments}
    assigned_detections = {item.detection_index for item in assignments}
    return MatchingResult(
        assignments=tuple(assignments),
        unmatched_components=tuple(
            index for index in range(count_ref) if index not in assigned_components
        ),
        unmatched_detections=tuple(
            index for index in range(count_det) if index not in assigned_detections
        ),
        cost_total=round(sum(item.cost for item in assignments), 4),
    )
