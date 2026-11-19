from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from ..config import BASE_DIR, settings

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


async def save_upload(file: UploadFile) -> dict:
    """Yüklenen görüntüyü doğrular ve güvenli bir dosya adıyla kaydeder."""

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Desteklenen dosya türleri: {', '.join(sorted(ALLOWED_SUFFIXES))}",
        )

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Maksimum yükleme boyutu: {settings.max_upload_mb} MB",
        )

    try:
        with Image.open(BytesIO(content)) as probe:
            probe.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya geçerli bir görüntü değil",
        ) from exc

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    image_id = uuid4()
    stored_path = settings.upload_dir / f"{image_id}{suffix}"
    stored_path.write_bytes(content)

    return {
        "id": image_id,
        "filename": file.filename or "upload",
        "stored_path": str(stored_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "size_bytes": len(content),
        "width": width,
        "height": height,
        "content_type": file.content_type,
    }
