from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Verdict = Literal["PASS", "FAIL", "MANUAL_REVIEW"]
EngineMode = Literal["real", "mock"]
Severity = Literal["critical", "high", "medium", "low", "info"]


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


class ReferenceComponent(BaseModel):
    ref: str
    type: str
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)


class ReferenceBoard(BaseModel):
    name: str
    image_path: str
    components: list[ReferenceComponent]


class ReferenceIssue(BaseModel):
    ref: str
    expected_type: str
    issue: Literal[
        "missing_component", "wrong_component", "shifted_component", "extra_component"
    ]
    distance_px: float | None = None
    detected_type: str | None = None
    confidence: float | None = None
    x: float | None = None
    y: float | None = None


class ReferenceCheck(BaseModel):
    reference: str
    aligned: bool
    expected_count: int
    raw_component_detections: int
    qualified_component_detections: int
    matched_count: int
    missing_count: int
    wrong_count: int
    shifted_count: int
    extra_count: int
    issues: list[ReferenceIssue]


class ModelInfo(BaseModel):
    defect_model: str
    component_model: str | None = None
    device: str
    engine: EngineMode
    class_thresholds_applied: bool = False


class DecisionReason(BaseModel):
    code: str
    severity: Severity
    source: Literal["defect", "reference", "quality", "engine"]
    message: str


class Decision(BaseModel):
    verdict: Verdict
    reasons: list[DecisionReason]


class InspectionResult(BaseModel):
    image_id: UUID
    original_image_path: str
    filename: str
    verdict: Verdict
    decision: Decision
    engine: EngineMode
    model: ModelInfo
    defects: list[Detection]
    counts: dict[str, int]
    image_width: int
    image_height: int
    duration_ms: int
    annotated_image_path: str | None = None
    report_json_path: str | None = None
    report_pdf_path: str | None = None
    reference_check: ReferenceCheck | None = None
    created_at: datetime
