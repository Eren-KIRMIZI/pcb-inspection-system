from fastapi import APIRouter, File, UploadFile

from ..schemas import InspectionResult, UploadedImage
from ..services.inspection import inspect_image
from ..services.storage import save_upload

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post("", response_model=InspectionResult)
async def create_inspection(file: UploadFile = File(...)) -> InspectionResult:
    uploaded = UploadedImage(**await save_upload(file))
    return inspect_image(uploaded.id, uploaded.stored_path)
