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

export interface ReferenceCheck {
  reference: string
  aligned: boolean
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
