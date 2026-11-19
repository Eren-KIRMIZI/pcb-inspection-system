from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import BASE_DIR, settings

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _normalize_image(content: bytes) -> tuple[bytes, str, int, int]:
    """Görüntüyü doğrular, EXIF yönünü uygular ve saklanacak baytları döner."""

    try:
        with Image.open(BytesIO(content)) as original:
            image_format = original.format or "JPEG"
            orientation = original.getexif().get(274, 1)
            needs_conversion = image_format == "JPEG" and original.mode not in {"RGB", "L"}

            # EXIF yönü zaten doğruysa dosyayı yeniden kodlama: piksel değişimi model
            # çıktısını değiştirebilir ve gereksiz kalite kaybı oluşturur.
            if orientation == 1 and not needs_conversion:
                width, height = original.size
                if width < settings.min_image_width or height < settings.min_image_height:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Görüntü çok küçük: {width}x{height}. "
                            f"En az {settings.min_image_width}x{settings.min_image_height} gerekli."
                        ),
                    )
                return content, image_format.lower(), width, height

            with ImageOps.exif_transpose(original) as corrected:
                if needs_conversion:
                    corrected = corrected.convert("RGB")
                width, height = corrected.size

                if width < settings.min_image_width or height < settings.min_image_height:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Görüntü çok küçük: {width}x{height}. "
                            f"En az {settings.min_image_width}x{settings.min_image_height} gerekli."
                        ),
                    )

                buffer = BytesIO()
                corrected.save(buffer, format=image_format, quality=95)
                return buffer.getvalue(), image_format.lower(), width, height
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya geçerli bir görüntü değil",
        ) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Görüntü işlenemedi: {exc}",
        ) from exc


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

    normalized, image_format, width, height = _normalize_image(content)
    stored_suffix = ".jpg" if image_format == "jpeg" else f".{image_format}"

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    image_id = uuid4()
    stored_path = settings.upload_dir / f"{image_id}{stored_suffix}"
    stored_path.write_bytes(normalized)

    return {
        "id": image_id,
        "filename": file.filename or "upload",
        "stored_path": str(stored_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "size_bytes": len(normalized),
        "width": width,
        "height": height,
        "content_type": file.content_type,
    }
