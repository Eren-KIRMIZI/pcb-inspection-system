import type { InspectionResult } from './types'

export async function inspectImage(file: File): Promise<InspectionResult> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch('/api/v1/inspections', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? 'Analiz isteği başarısız oldu')
  }

  return response.json() as Promise<InspectionResult>
}

export function mediaUrl(path: string | null): string | null {
  if (!path) return null
  return `/${path.replace(/^data\//, 'media/')}`
}
