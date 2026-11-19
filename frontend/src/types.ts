export type Verdict = 'PASS' | 'FAIL' | 'MANUAL_REVIEW'
export type EngineMode = 'real' | 'mock'
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface Detection {
  class_id: number
  class_name: string
  confidence: number
  bbox: number[]
}

export interface DecisionReason {
  code: string
  severity: Severity
  source: 'defect' | 'reference' | 'quality' | 'engine'
  message: string
}

export interface Decision {
  verdict: Verdict
  reasons: DecisionReason[]
}

export interface ModelInfo {
  defect_model: string
  component_model: string | null
  device: string
  engine: EngineMode
  class_thresholds_applied: boolean
}

export interface ReferenceIssue {
  ref: string
  expected_type: string
  issue: 'missing_component' | 'wrong_component' | 'shifted_component' | 'extra_component'
  distance_px: number | null
  detected_type: string | null
  confidence: number | null
  x: number | null
  y: number | null
}

export interface AlignmentInfo {
  trusted: boolean
  inlier_count: number
  inlier_ratio: number
  scale: number | null
  rotation_deg: number | null
  reason: string
}

export interface ReferenceCheck {
  reference: string
  aligned: boolean
  alignment: AlignmentInfo | null
  expected_count: number
  raw_component_detections: number
  qualified_component_detections: number
  matched_count: number
  missing_count: number
  wrong_count: number
  shifted_count: number
  extra_count: number
  issues: ReferenceIssue[]
}

export interface InspectionResult {
  image_id: string
  original_image_path: string
  filename: string
  verdict: Verdict
  decision: Decision
  engine: EngineMode
  model: ModelInfo
  defects: Detection[]
  counts: Record<string, number>
  image_width: number
  image_height: number
  duration_ms: number
  annotated_image_path: string | null
  report_json_path: string | null
  report_pdf_path: string | null
  reference_check: ReferenceCheck | null
  created_at: string
}

export interface HistoryEntry {
  image_id: string
  created_at: string
  filename: string
  verdict: Verdict
  engine: EngineMode
  defect_count: number
  top_defect: string | null
  reference_name: string | null
  reference_issues: number
  duration_ms: number
  image_width: number
  image_height: number
  annotated_image_path: string | null
  report_json_path: string | null
  report_pdf_path: string | null
}

export interface TrendPoint {
  date: string
  total: number
  pass_count: number
  fail_count: number
  manual_review_count: number
}

export interface DefectCount {
  class_name: string
  count: number
}

export interface OverviewPeriod {
  start: string
  end: string
  days: number
}

export interface PeriodComparison {
  total_inspections: number
  total_delta: number
  total_change_pct: number | null
  defect_count: number
  defect_delta: number
  defect_change_pct: number | null
}

export interface OverviewStats {
  total_inspections: number
  all_time_count: number
  pass_count: number
  fail_count: number
  manual_review_count: number
  pass_rate: number
  defect_count: number
  reference_checks: number
  period: OverviewPeriod
  previous: PeriodComparison | null
  trend: TrendPoint[]
  defect_distribution: DefectCount[]
  recent: HistoryEntry[]
}

export interface ReferenceComponent {
  ref: string
  type: string
  x: number
  y: number
}

export interface ReferenceBoard {
  name: string
  image_path: string
  components: ReferenceComponent[]
}

export interface ReferenceSummary {
  name: string
  component_count: number
  image_path: string
}

export interface ModelCard {
  id: string
  name: string
  role: string
  status: 'active' | 'configured' | 'disabled'
  weights: string | null
  map50: number | null
  map50_95: number | null
  source: string
  classes: string[]
  note: string
}

export interface ModelPerformance {
  measured_in_app: boolean
  models: ModelCard[]
  unmeasured_metrics: string[]
  limitations: string[]
}

export interface SettingsResponse {
  device: string
  engine: EngineMode
  defect_model: string
  component_model: string | null
  conf_threshold: number
  class_thresholds_applied: boolean
  component_conf_threshold: number
  component_imgsz: number
  reference_component_min_confidence: number
  reference_match_distance_ratio: number
  reference_shift_distance_ratio: number
  min_image_width: number
  min_image_height: number
  max_upload_mb: number
}

export interface ResourceStatus {
  key: string
  label: string
  status: 'ok' | 'warning' | 'error'
  detail: string
}

export interface SystemStatus {
  api: ResourceStatus
  defect_model: ResourceStatus
  component_model: ResourceStatus
  storage: ResourceStatus
  database: ResourceStatus
}
