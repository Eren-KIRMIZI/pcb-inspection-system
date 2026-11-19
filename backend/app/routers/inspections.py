from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..schemas import InspectionResult, UploadedImage
from ..services.inspection import inspect_image
from ..services.reference import load_reference
from ..services.storage import save_upload

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post("", response_model=InspectionResult)
async def create_inspection(
    file: UploadFile = File(...),
    reference_name: str | None = Form(None),
) -> InspectionResult:
    uploaded = UploadedImage(**await save_upload(file))

    reference = None
    if reference_name:
        reference = load_reference(reference_name)
        if reference is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referans bulunamadı: {reference_name}",
            )

    return inspect_image(uploaded, reference)
