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


class ErrorResponse(BaseModel):
    """Tüm hata cevaplarının ortak gövdesi."""

    error: str
    detail: str
    request_id: str | None = None


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


class HistoryEntry(BaseModel):
    image_id: UUID
    created_at: datetime
    filename: str
    verdict: Verdict
    engine: EngineMode
    defect_count: int
    top_defect: str | None = None
    reference_name: str | None = None
    reference_issues: int = 0
    duration_ms: int
    image_width: int
    image_height: int
    annotated_image_path: str | None = None
    report_json_path: str | None = None
    report_pdf_path: str | None = None


class TrendPoint(BaseModel):
    date: str
    total: int
    pass_count: int
    fail_count: int
    manual_review_count: int


class DefectCount(BaseModel):
    class_name: str
    count: int


class OverviewPeriod(BaseModel):
    start: str
    end: str
    days: int


class PeriodComparison(BaseModel):
    total_inspections: int
    total_delta: int
    total_change_pct: float | None = None
    defect_count: int
    defect_delta: int
    defect_change_pct: float | None = None


class OverviewStats(BaseModel):
    total_inspections: int
    all_time_count: int
    pass_count: int
    fail_count: int
    manual_review_count: int
    pass_rate: float
    defect_count: int
    reference_checks: int
    period: OverviewPeriod
    previous: PeriodComparison | None = None
    trend: list[TrendPoint]
    defect_distribution: list[DefectCount]
    recent: list[HistoryEntry]


class ReferenceSummary(BaseModel):
    name: str
    component_count: int
    image_path: str


class ModelCard(BaseModel):
    id: str
    name: str
    role: str
    status: Literal["active", "configured", "disabled"]
    weights: str | None = None
    map50: float | None = None
    map50_95: float | None = None
    source: str
    classes: list[str] = []
    note: str


class ModelPerformance(BaseModel):
    measured_in_app: bool
    models: list[ModelCard]
    unmeasured_metrics: list[str]
    limitations: list[str]


class SettingsResponse(BaseModel):
    device: str
    engine: EngineMode
    defect_model: str
    component_model: str | None
    conf_threshold: float
    class_thresholds_applied: bool
    component_conf_threshold: float
    component_imgsz: int
    reference_component_min_confidence: float
    reference_match_distance_ratio: float
    reference_shift_distance_ratio: float
    min_image_width: int
    min_image_height: int
    max_upload_mb: int


class ResourceStatus(BaseModel):
    key: str
    label: str
    status: Literal["ok", "warning", "error"]
    detail: str


class SystemStatus(BaseModel):
    api: ResourceStatus
    defect_model: ResourceStatus
    component_model: ResourceStatus
    storage: ResourceStatus
    database: ResourceStatus
