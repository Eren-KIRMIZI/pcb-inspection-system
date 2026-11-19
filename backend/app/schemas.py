from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str


class UploadedImage(BaseModel):
    id: UUID
    filename: str
    stored_path: str
    size_bytes: int
    width: int
    height: int
    content_type: str | None = None


class Detection(BaseModel):
    class_id: int
    class_name: str
    confidence: float = Field(..., ge=0, le=1)
    bbox: list[float] = Field(..., min_length=4, max_length=4)


class InspectionResult(BaseModel):
    image_id: UUID
    verdict: str
    defects: list[Detection]
    counts: dict[str, int]
    annotated_image_path: str | None = None
    created_at: datetime
