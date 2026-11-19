from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from ..config import BASE_DIR
from ..schemas import InspectionResult
from .annotation import draw_detections
from .decision import decide
from .detector import get_detector
from .report import generate_reports


def _relative(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def inspect_image(image_id: UUID, stored_path: str) -> InspectionResult:
    """Yüklenen görüntü için tespit, görselleştirme ve ilk kararı üretir."""

    image_path = BASE_DIR / stored_path
    detections = get_detector().predict(image_path)
    annotated_path = draw_detections(image_path, detections)

    counts: dict[str, int] = {}
    for detection in detections:
        counts[detection.class_name] = counts.get(detection.class_name, 0) + 1

    result = InspectionResult(
        image_id=image_id,
        verdict=decide(detections),
        defects=detections,
        counts=counts,
        annotated_image_path=_relative(annotated_path),
        created_at=datetime.now(timezone.utc),
    )
    result.report_json_path, result.report_pdf_path = generate_reports(result)
    return result
