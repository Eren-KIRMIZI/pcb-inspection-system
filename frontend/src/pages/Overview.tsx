import { useCallback, useEffect, useState } from 'react'
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
import { getOverview, getSettings } from '../api'
import type { OverviewStats, SettingsResponse } from '../types'
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

export function Overview({
  onNavigate,
  onOpenInspection,
}: {
  onNavigate: (page: PageKey) => void
  onOpenInspection: (id: string) => void
}) {
  const [stats, setStats] = useState<OverviewStats | null>(null)
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [overview, config] = await Promise.all([getOverview(7), getSettings()])
      setStats(overview)
      setSettings(config)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Veriler yüklenemedi')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return (
    <div className="page">
      <PageHeader
        eyebrow="ÜRETİM ÖZETİ"
        title="Genel Bakış"
        description="Gerçek analiz kayıtlarından hesaplanan kalite göstergeleri."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => onNavigate('inspection')}>
            <Icon name="inspection" size={16} /> Yeni analiz
          </button>
        }
      />

      {loading && <LoadingBlock label="İstatistikler hazırlanıyor…" />}
      {error && <ErrorBlock message={error} onRetry={() => void load()} />}

      {stats && !loading && !error && (
        <>
          <div className="stat-grid">
            <StatCard label="Toplam İncelenen PCB" value={stats.total_inspections} hint="kayıtlı analiz" tone="info" />
            <StatCard label="PASS Oranı" value={`%${stats.pass_rate.toFixed(1)}`} hint={`${stats.pass_count} başarılı`} tone="pass" />
            <StatCard label="FAIL" value={stats.fail_count} hint="kalite dışı kart" tone="fail" />
            <StatCard label="Manuel İnceleme" value={stats.manual_review_count} hint="karar bekliyor" tone="review" />
          </div>

          {stats.total_inspections === 0 ? (
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
          ) : (
            <div className="dashboard-grid">
              <Card title="Analiz Trendi" subtitle="Son 7 gün · karar bazında">
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

              <Card title="Kusur Dağılımı" subtitle="Tüm analizlerdeki tespit sayıları">
                {stats.defect_distribution.length === 0 ? (
                  <EmptyBlock title="Kusur tespit edilmedi" description="Şu ana kadar kaydedilen analizlerde kusur bulunamadı." />
                ) : (
                  <div className="chart-box">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.defect_distribution} layout="vertical" margin={{ left: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                        <YAxis type="category" dataKey="class_name" width={130} tick={{ fontSize: 10 }} />
                        <Tooltip />
                        <Bar dataKey="count" name="Tespit" radius={[0, 3, 3, 0]}>
                          {stats.defect_distribution.map((entry) => (
                            <Cell key={entry.class_name} fill="#f97316" />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              <Card title="Son Analizler" className="span-2" actions={
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

              <Card title="Motor Durumu">
                {settings && (
                  <div className="status-list">
                    <div><span>Motor</span><strong>{settings.engine === 'real' ? 'Gerçek YOLO' : 'Mock'}</strong></div>
                    <div><span>Cihaz</span><strong>{settings.device}</strong></div>
                    <div><span>Kusur modeli</span><strong title={settings.defect_model}>{settings.defect_model.split('/').pop()}</strong></div>
                    <div><span>Komponent modeli</span><strong>{settings.component_model ? 'etkin' : 'kapalı'}</strong></div>
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
