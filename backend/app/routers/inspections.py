from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..config import BASE_DIR
from ..schemas import InspectionResult, UploadedImage
from ..services.components import get_component_detector
from ..services.inspection import inspect_image
from ..services.reference import compare_board, load_reference
from ..services.storage import save_upload

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post("", response_model=InspectionResult)
async def create_inspection(
    file: UploadFile = File(...),
    reference_name: str | None = Form(None),
) -> InspectionResult:
    uploaded = UploadedImage(**await save_upload(file))
    result = inspect_image(uploaded.id, uploaded.stored_path)

    if reference_name:
        reference = load_reference(reference_name)
        if reference is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referans bulunamadı: {reference_name}",
            )
        detector = get_component_detector()
        target_path = BASE_DIR / uploaded.stored_path
        component_detections = detector.predict(target_path) if detector else []
        result.reference_check = compare_board(reference, target_path, component_detections)

    return result
