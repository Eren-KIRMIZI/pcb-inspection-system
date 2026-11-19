from fastapi import APIRouter, File, UploadFile

from ..schemas import UploadedImage
from ..services.storage import save_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadedImage)
async def upload_image(file: UploadFile = File(...)) -> UploadedImage:
    return UploadedImage(**await save_upload(file))
