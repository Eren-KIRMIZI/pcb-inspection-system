from uuid import UUID

from pydantic import BaseModel


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
