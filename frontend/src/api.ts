import type {
  HistoryEntry,
  InspectionResult,
  ModelPerformance,
  OverviewStats,
  ReferenceBoard,
  ReferenceSummary,
  SettingsResponse,
  SystemStatus,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init)
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `İstek başarısız (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function inspectImage(file: File, referenceName?: string): Promise<InspectionResult> {
  const formData = new FormData()
  formData.append('file', file)
  if (referenceName) formData.append('reference_name', referenceName)
  return request<InspectionResult>('/inspections', { method: 'POST', body: formData })
}

export async function createReference(
  name: string,
  image: File,
  bom: File,
): Promise<ReferenceBoard> {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('image', image)
  formData.append('bom', bom)
  return request<ReferenceBoard>('/references', { method: 'POST', body: formData })
}

export interface OverviewQuery {
  days?: number
  date_from?: string
  date_to?: string
}

export function getOverview(query: OverviewQuery = { days: 7 }): Promise<OverviewStats> {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  const suffix = params.toString()
  return request<OverviewStats>(`/history/overview${suffix ? `?${suffix}` : ''}`)
}

export interface HistoryQuery {
  limit?: number
  offset?: number
  verdict?: string
  engine?: string
  search?: string
}

export function getHistory(query: HistoryQuery = {}): Promise<HistoryEntry[]> {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  const suffix = params.toString()
  return request<HistoryEntry[]>(`/history${suffix ? `?${suffix}` : ''}`)
}

export function getInspection(id: string): Promise<InspectionResult> {
  return request<InspectionResult>(`/history/${id}`)
}

export function getReferences(): Promise<ReferenceSummary[]> {
  return request<ReferenceSummary[]>('/references')
}

export function getReference(name: string): Promise<ReferenceBoard> {
  return request<ReferenceBoard>(`/references/${encodeURIComponent(name)}`)
}

export function getModels(): Promise<ModelPerformance> {
  return request<ModelPerformance>('/models')
}

export function getSettings(): Promise<SettingsResponse> {
  return request<SettingsResponse>('/settings')
}

export function getSystemStatus(): Promise<SystemStatus> {
  return request<SystemStatus>('/status')
}

export function mediaUrl(path: string | null): string | null {
  if (!path) return null
  return `/${path.replace(/^data\//, 'media/')}`
}

export function downloadUrl(path: string | null): string | undefined {
  return mediaUrl(path) ?? undefined
}
