export interface Detection {
  class_id: number
  class_name: string
  confidence: number
  bbox: number[]
}

export interface InspectionResult {
  image_id: string
  verdict: string
  defects: Detection[]
  counts: Record<string, number>
  annotated_image_path: string | null
  created_at: string
}
