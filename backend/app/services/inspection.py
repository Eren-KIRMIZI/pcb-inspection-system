from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from ..config import BASE_DIR, settings
from ..logging_config import get_logger
from ..schemas import (
    InspectionResult,
    ModelInfo,
    ReferenceBoard,
    UploadedImage,
)
from .annotation import draw_detections
from .components import get_component_detector
from .decision import DecisionContext, decide
from .detector import get_detector
from .history import save_result
from .reference import compare_board
from .report import generate_reports

logger = get_logger(__name__)


def _relative(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def _model_info(engine: str, component_used: bool) -> ModelInfo:
    detector = get_detector()
    return ModelInfo(
        defect_model=settings.defect_model_name if engine == "real" else detector.name,
        component_model=settings.component_model_name if component_used else None,
        device=settings.device,
        engine=detector.engine,
        class_thresholds_applied=getattr(detector, "thresholds_applied", False),
    )


def inspect_image(
    uploaded: UploadedImage,
    reference: ReferenceBoard | None = None,
) -> InspectionResult:
    """Yükleme → tespit → referans → karar → rapor akışını yönetir."""

    started = perf_counter()
    image_path = BASE_DIR / uploaded.stored_path

    detector = get_detector()
    defects = detector.predict(image_path)

    reference_check = None
    if reference is not None:
        component_detector = get_component_detector()
        component_detections = (
            component_detector.predict(image_path) if component_detector else []
        )
        reference_check = compare_board(reference, image_path, component_detections)

    quality_ok = (
        uploaded.width >= settings.min_image_width
        and uploaded.height >= settings.min_image_height
    )
    decision = decide(
        DecisionContext(
            defects=defects,
            reference_check=reference_check,
            engine=detector.engine,
            image_quality_ok=quality_ok,
            image_width=uploaded.width,
            image_height=uploaded.height,
        )
    )

    annotated_path = draw_detections(image_path, defects)
    counts: dict[str, int] = {}
    for defect in defects:
        counts[defect.class_name] = counts.get(defect.class_name, 0) + 1

    result = InspectionResult(
        image_id=uploaded.id,
        original_image_path=uploaded.stored_path,
        filename=uploaded.filename,
        verdict=decision.verdict,
        decision=decision,
        engine=detector.engine,
        model=_model_info(detector.engine, reference is not None),
        defects=defects,
        counts=counts,
        image_width=uploaded.width,
        image_height=uploaded.height,
        duration_ms=int((perf_counter() - started) * 1000),
        annotated_image_path=_relative(annotated_path),
        reference_check=reference_check,
        created_at=datetime.now(timezone.utc),
    )
    result.report_json_path, result.report_pdf_path = generate_reports(result)
    save_result(result)

    logger.info(
        "Analiz tamamlandı",
        extra={
            "event": "inspection_completed",
            "image_id": str(result.image_id),
            "upload_filename": result.filename,
            "engine": result.engine,
            "defect_model": result.model.defect_model,
            "component_model": result.model.component_model,
            "device": result.model.device,
            "verdict": result.verdict,
            "defect_count": len(result.defects),
            "decision_codes": [reason.code for reason in result.decision.reasons],
            "reference": result.reference_check.reference
            if result.reference_check
            else None,
            "reference_issues": len(result.reference_check.issues)
            if result.reference_check
            else None,
            "duration_ms": result.duration_ms,
        },
    )
    return result
