import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getOverview, getSettings, getSystemStatus } from '../api'
import type { OverviewQuery } from '../api'
import type {
  OverviewStats,
  ResourceStatus,
  SettingsResponse,
  SystemStatus,
} from '../types'
import { defectLabel } from '../labels'
import type { PageKey } from '../components/Sidebar'
import {
  Card,
  EmptyBlock,
  ErrorBlock,
  Icon,
  LoadingBlock,
  PageHeader,
  StatCard,
  VerdictBadge,
  formatDate,
  formatDuration,
} from '../components/ui'

const CHART_COLORS: Record<string, string> = {
  pass_count: '#22c55e',
  fail_count: '#ef4444',
  manual_review_count: '#f59e0b',
}

const PRESETS = [
  { key: '7', label: '7 gün' },
  { key: '30', label: '30 gün' },
  { key: '90', label: '90 gün' },
  { key: 'custom', label: 'Özel' },
] as const

type PeriodPreset = (typeof PRESETS)[number]['key']

function isoDay(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

function Delta({
  value,
  percent,
  goodWhenUp = true,
}: {
  value: number
  percent: number | null
  goodWhenUp?: boolean
}) {
  if (value === 0) {
    return <span className="delta delta-flat">±0 · değişim yok</span>
  }
  const good = value > 0 ? goodWhenUp : !goodWhenUp
  return (
    <span className={`delta ${good ? 'delta-good' : 'delta-bad'}`}>
      {value > 0 ? '+' : ''}
      {value}
      {percent !== null ? ` (%${percent > 0 ? '+' : ''}${percent})` : ''}
    </span>
  )
}

export function Overview({
  onNavigate,
  onOpenInspection,
}: {
  onNavigate: (page: PageKey) => void
  onOpenInspection: (id: string) => void
}) {
  const today = useMemo(() => new Date(), [])
  const [stats, setStats] = useState<OverviewStats | null>(null)
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [preset, setPreset] = useState<PeriodPreset>('7')
  const [customFrom, setCustomFrom] = useState(
    isoDay(new Date(today.getTime() - 29 * 86_400_000)),
  )
  const [customTo, setCustomTo] = useState(isoDay(today))

  const query = useMemo<OverviewQuery>(
    () => (preset === 'custom'
      ? { date_from: customFrom, date_to: customTo }
      : { days: Number(preset) }),
    [preset, customFrom, customTo],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [overview, config, system] = await Promise.all([
        getOverview(query),
        getSettings(),
        getSystemStatus().catch(() => null),
      ])
      setStats(overview)
      setSettings(config)
      setStatus(system)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Veriler yüklenemedi')
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => { void load() }, [load])

  const resources: ResourceStatus[] = status ? Object.values(status) : []
  const defectChartData = (stats?.defect_distribution ?? []).map((entry) => ({
    ...entry,
    label: defectLabel(entry.class_name),
  }))
  const previous = stats?.previous ?? null

  return (
    <div className="page">
      <PageHeader
        eyebrow="ÜRETİM ÖZETİ"
        title="Genel Bakış"
        description="Seçili dönemdeki gerçek analiz kayıtlarından hesaplanan kalite göstergeleri."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => onNavigate('inspection')}>
            <Icon name="inspection" size={16} /> Yeni analiz
          </button>
        }
      />

      <div className="period-bar">
        <div className="period-presets" role="group" aria-label="Tarih aralığı">
          {PRESETS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={preset === item.key ? 'period-active' : ''}
              onClick={() => setPreset(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        {stats && (
          <span className="period-range">
            {stats.period.start} → {stats.period.end} · {stats.period.days} gün
          </span>
        )}
        {preset === 'custom' && (
          <div className="period-custom">
            <input
              type="date"
              className="input"
              aria-label="Başlangıç tarihi"
              value={customFrom}
              max={customTo}
              onChange={(event) => {
                const value = event.target.value
                setCustomFrom(value)
                if (value > customTo) setCustomTo(value)
              }}
            />
            <span className="muted">—</span>
            <input
              type="date"
              className="input"
              aria-label="Bitiş tarihi"
              value={customTo}
              min={customFrom}
              onChange={(event) => {
                const value = event.target.value
                setCustomTo(value)
                if (value < customFrom) setCustomFrom(value)
              }}
            />
          </div>
        )}
      </div>

      {loading && <LoadingBlock label="İstatistikler hazırlanıyor…" />}
      {error && <ErrorBlock message={error} onRetry={() => void load()} />}

      {stats && !loading && !error && (
        <>
          <div className="stat-grid five">
            <StatCard
              label="Dönem Analizi"
              value={stats.total_inspections}
              hint={
                <span className="delta-line">
                  <span>tüm zamanlar: {stats.all_time_count} · önceki: {previous?.total_inspections ?? 0}</span>
                  {previous && <Delta value={previous.total_delta} percent={previous.total_change_pct} />}
                </span>
              }
              tone="info"
            />
            <StatCard
              label="PASS Oranı"
              value={`%${stats.pass_rate.toFixed(1)}`}
              hint={`${stats.pass_count} başarılı · ${stats.fail_count} FAIL`}
              tone="pass"
            />
            <StatCard
              label="Kusur Tespiti"
              value={stats.defect_count}
              hint={
                <span className="delta-line">
                  <span>önceki: {previous?.defect_count ?? 0}</span>
                  {previous && (
                    <Delta
                      value={previous.defect_delta}
                      percent={previous.defect_change_pct}
                      goodWhenUp={false}
                    />
                  )}
                </span>
              }
            />
            <StatCard label="FAIL" value={stats.fail_count} hint="kalite dışı kart" tone="fail" />
            <StatCard
              label="Manuel İnceleme"
              value={stats.manual_review_count}
              hint="karar bekliyor"
              tone="review"
            />
          </div>

          {stats.all_time_count === 0 ? (
            <Card>
              <EmptyBlock
                title="Henüz analiz kaydı yok"
                description="İlk PCB görüntüsünü yüklediğinizde KPI'lar ve grafikler gerçek verilerle dolar."
                action={
                  <button type="button" className="btn btn-primary" onClick={() => onNavigate('inspection')}>
                    Analiz yap
                  </button>
                }
              />
            </Card>
          ) : stats.total_inspections === 0 ? (
            <Card>
              <EmptyBlock
                title="Bu dönemde analiz kaydı yok"
                description="Tarih aralığını değiştirin veya yeni bir analiz gerçekleştirin."
                action={
                  <button type="button" className="btn btn-ghost" onClick={() => setPreset('7')}>
                    Son 7 güne dön
                  </button>
                }
              />
            </Card>
          ) : (
            <div className="dashboard-grid">
              <Card title="Analiz Trendi" subtitle={`${stats.period.days} gün · karar bazında`}>
                <div className="chart-box">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={stats.trend} barGap={2}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(value: string) => value.slice(5)} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="pass_count" name="PASS" fill={CHART_COLORS.pass_count} radius={[3, 3, 0, 0]} />
                      <Bar dataKey="fail_count" name="FAIL" fill={CHART_COLORS.fail_count} radius={[3, 3, 0, 0]} />
                      <Bar dataKey="manual_review_count" name="MANUEL" fill={CHART_COLORS.manual_review_count} radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card title="Kusur Dağılımı" subtitle="Seçili dönemdeki tespit sayıları">
                {defectChartData.length === 0 ? (
                  <EmptyBlock title="Kusur tespit edilmedi" description="Bu dönemde kaydedilen analizlerde kusur bulunamadı." />
                ) : (
                  <div className="chart-box">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={defectChartData} layout="vertical" margin={{ left: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                        <YAxis type="category" dataKey="label" width={130} tick={{ fontSize: 10 }} />
                        <Tooltip />
                        <Bar dataKey="count" name="Tespit" radius={[0, 3, 3, 0]}>
                          {defectChartData.map((entry) => (
                            <Cell key={entry.class_name} fill="#f97316" />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card title="Son Analizler" className="span-2" subtitle="Yalnızca seçili dönem" actions={
                <button type="button" className="link-btn" onClick={() => onNavigate('history')}>
                  Tümünü gör <Icon name="chevron" size={14} />
                </button>
              }>
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Kart</th>
                        <th>Karar</th>
                        <th>Kusur</th>
                        <th>Referans</th>
                        <th>Süre</th>
                        <th>Tarih</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recent.map((entry) => (
                        <tr key={entry.image_id} className="clickable-row" onClick={() => onOpenInspection(entry.image_id)}>
                          <td className="mono">{entry.filename}</td>
                          <td><VerdictBadge verdict={entry.verdict} /></td>
                          <td>{entry.defect_count}</td>
                          <td>{entry.reference_name ?? '—'}</td>
                          <td>{formatDuration(entry.duration_ms)}</td>
                          <td>{formatDate(entry.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card title="Sistem Durumu" subtitle="API · model dosyaları · depolama · veritabanı">
                {status ? (
                  <div className="status-list">
                    {resources.map((resource) => (
                      <div key={resource.key} title={resource.detail}>
                        <span className="status-resource">
                          <span className={`status-dot status-dot-${resource.status}`} /> {resource.label}
                        </span>
                        <strong>{resource.detail}</strong>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="muted">Sistem durumu API'den alınamadı.</p>
                )}
                {settings && (
                  <div className="status-list">
                    <div><span>Motor</span><strong>{settings.engine === 'real' ? 'Gerçek YOLO' : 'Mock'}</strong></div>
                    <div><span>Cihaz</span><strong>{settings.device}</strong></div>
                    <div><span>Sınıf eşikleri</span><strong>{settings.class_thresholds_applied ? 'etkin' : 'kapalı'}</strong></div>
                    <div><span>Referans kontrolü</span><strong>{stats.reference_checks} analiz</strong></div>
                  </div>
                )}
                <button type="button" className="link-btn" onClick={() => onNavigate('models')}>
                  Model performansını gör <Icon name="chevron" size={14} />
                </button>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  )
}
