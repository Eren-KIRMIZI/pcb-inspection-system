import type { ReactNode } from 'react'
import type { EngineMode, Severity, Verdict } from '../types'

const ICON_PATHS: Record<string, string> = {
  overview: 'M3 3h7v7H3V3zm11 0h7v7h-7V3zM3 14h7v7H3v-7zm11 0h7v7h-7v-7z',
  inspection: 'M12 5v14M5 12h14',
  history: 'M12 8v4l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z',
  reference: 'M4 6h16M4 12h16M4 18h10',
  reports: 'M7 3h7l5 5v13H7V3zm7 0v5h5',
  model: 'M4 20V10m5 10V4m5 16v-7m5 7V8',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8-3l2-1-2-3-2 1-2-1V5h-4v3l-2 1-2-1-2 3 2 1v4l-2 1 2 3 2-1 2 1v3h4v-3l2-1 2 1 2-3-2-1v-4z',
  upload: 'M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4',
  shield: 'M12 3l8 3v6c0 5-3.4 8.3-8 9-4.6-.7-8-4-8-9V6l8-3z',
  search: 'M10 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm5 11 5 5',
  download: 'M12 4v12m-5-5 5 5 5-5M4 18v2h16v-2',
  zoomIn: 'M10 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 4v4m-2-2h4m3 7 5 5',
  zoomOut: 'M10 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm-2 6h4m3 5 5 5',
  fit: 'M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5',
  layers: 'M12 3 3 8l9 5 9-5-9-5zm-9 9 9 5 9-5M3 16l9 5 9-5',
  check: 'M5 12l4 4L19 6',
  alert: 'M12 4 2 20h20L12 4zm0 6v5m0 3h.01',
  clock: 'M12 8v4l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z',
  image: 'M4 5h16v14H4V5zm3 10 3-4 3 3 3-5 4 6',
  close: 'M6 6l12 12M18 6 6 18',
  chevron: 'M9 6l6 6-6 6',
}

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={ICON_PATHS[name] ?? ICON_PATHS.overview} />
    </svg>
  )
}

const VERDICT_LABEL: Record<Verdict, string> = {
  PASS: 'PASS',
  FAIL: 'FAIL',
  MANUAL_REVIEW: 'MANUEL İNCELEME',
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return <span className={`badge verdict-${verdict.toLowerCase()}`}>{VERDICT_LABEL[verdict]}</span>
}

export function EngineBadge({ engine }: { engine: EngineMode }) {
  return (
    <span className={`badge engine-${engine}`}>
      {engine === 'mock' ? 'MOCK MOTOR' : 'GERÇEK MODEL'}
    </span>
  )
}

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'kritik',
  high: 'yüksek',
  medium: 'orta',
  low: 'düşük',
  info: 'bilgi',
}

export function SeverityPill({ severity }: { severity: Severity }) {
  return <span className={`severity severity-${severity}`}>{SEVERITY_LABEL[severity]}</span>
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  className = '',
}: {
  title?: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </section>
  )
}

export function StatCard({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string
  value: string | number
  hint?: string
  tone?: 'default' | 'pass' | 'fail' | 'review' | 'info'
}) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  )
}

export function LoadingBlock({ label = 'Yükleniyor…' }: { label?: string }) {
  return (
    <div className="state-block" role="status">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  )
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-block state-error" role="alert">
      <Icon name="alert" size={22} />
      <div>
        <strong>Bir sorun oluştu</strong>
        <p>{message}</p>
      </div>
      {onRetry && (
        <button className="btn btn-ghost" onClick={onRetry} type="button">
          Tekrar dene
        </button>
      )}
    </div>
  )
}

export function EmptyBlock({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="state-block state-empty">
      <Icon name="layers" size={24} />
      <div>
        <strong>{title}</strong>
        {description && <p className="muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function formatDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('tr-TR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
}

export function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} sn` : `${ms} ms`
}
