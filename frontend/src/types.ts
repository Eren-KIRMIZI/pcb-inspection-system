export interface Detection {
  class_id: number
  class_name: string
  confidence: number
  bbox: number[]
}

export interface ReferenceIssue {
  ref: string
  expected_type: string
  issue: 'missing_component' | 'wrong_component' | 'shifted_component'
  distance_px: number | null
  detected_type: string | null
  confidence: number | null
}

export interface ReferenceCheck {
  reference: string
  aligned: boolean
  expected_count: number
  detected_count: number
  issues: ReferenceIssue[]
}

export interface InspectionResult {
  image_id: string
  verdict: string
  defects: Detection[]
  counts: Record<string, number>
  annotated_image_path: string | null
  report_json_path: string | null
  report_pdf_path: string | null
  reference_check: ReferenceCheck | null
  created_at: string
}
