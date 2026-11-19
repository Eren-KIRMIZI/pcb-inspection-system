import json
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..schemas import ReferenceBoard, ReferenceComponent, UploadedImage
from ..services.reference import load_reference, save_reference
from ..services.storage import save_upload

router = APIRouter(prefix="/references", tags=["references"])


@router.post("", response_model=ReferenceBoard)
async def create_reference(
    name: str = Form(...),
    image: UploadFile = File(...),
    bom: UploadFile = File(...),
) -> ReferenceBoard:
    uploaded = UploadedImage(**await save_upload(image))

    try:
        payload = json.loads(await bom.read())
        items = payload.get("components") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise ValueError("BOM dosyasında 'components' listesi bulunamadı")
        components = [ReferenceComponent.model_validate(item) for item in items]
        board = ReferenceBoard(
            name=name,
            image_path=uploaded.stored_path,
            components=components,
        )
        save_reference(board)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return board


@router.get("/{name}", response_model=ReferenceBoard)
def get_reference(name: str) -> ReferenceBoard:
    board = load_reference(name)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referans bulunamadı")
    return board
