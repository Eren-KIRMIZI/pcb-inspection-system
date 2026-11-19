import { useCallback, useEffect, useState } from 'react'
import { downloadUrl, getHistory, getInspection, mediaUrl } from '../api'
import type { HistoryEntry, InspectionResult } from '../types'
import { ResultPanel } from '../components/ResultPanel'
import {
  Card,
  EmptyBlock,
  ErrorBlock,
  Icon,
  LoadingBlock,
  PageHeader,
  VerdictBadge,
  formatDateTime,
} from '../components/ui'

export function QualityReports() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [selected, setSelected] = useState<InspectionResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setEntries(await getHistory({ limit: 50 }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Raporlar yüklenemedi')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const openReport = async (id: string) => {
    try {
      setSelected(await getInspection(id))
    } catch {
      setSelected(null)
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="DOKÜMANTASYON"
        title="Kalite Raporları"
        description="Her analiz için JSON ve PDF raporu; karar gerekçeleriyle birlikte."
        actions={
          <button type="button" className="btn btn-ghost" onClick={() => void load()}>
            <Icon name="fit" size={15} /> Yenile
          </button>
        }
      />

      {loading && <LoadingBlock label="Raporlar hazırlanıyor…" />}
      {error && <ErrorBlock message={error} onRetry={() => void load()} />}

      {!loading && !error && entries.length === 0 && (
        <Card>
          <EmptyBlock title="Henüz rapor yok" description="Analiz tamamlandığında JSON ve PDF raporları burada listelenir." />
        </Card>
      )}

      <div className="report-layout">
        <Card title={`Rapor Listesi (${entries.length})`} className="report-list-card">
          <div className="report-list">
            {entries.map((entry) => (
              <div className={`report-item ${selected?.image_id === entry.image_id ? 'report-item-active' : ''}`} key={entry.image_id}>
                <div className="report-thumb">
                  {mediaUrl(entry.annotated_image_path) ? (
                    <img src={mediaUrl(entry.annotated_image_path)!} alt="" />
                  ) : (
                    <Icon name="image" size={20} />
                  )}
                </div>
                <div className="report-info">
                  <strong title={entry.filename}>{entry.filename}</strong>
                  <span>{formatDateTime(entry.created_at)}</span>
                  <div className="report-badges">
                    <VerdictBadge verdict={entry.verdict} />
                    {entry.reference_name && <span className="badge badge-neutral">REF: {entry.reference_name}</span>}
                  </div>
                </div>
                <div className="report-actions">
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => void openReport(entry.image_id)}>
                    Aç
                  </button>
                  {entry.report_pdf_path && (
                    <a className="icon-btn" href={downloadUrl(entry.report_pdf_path)} download title="PDF indir">
                      <Icon name="download" size={15} />
                    </a>
                  )}
                  {entry.report_json_path && (
                    <a className="icon-btn" href={downloadUrl(entry.report_json_path)} download title="JSON indir">
                      <Icon name="reports" size={15} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="report-detail">
          {selected ? (
            <>
              <div className="section-caption">Seçili rapor · {selected.image_id.slice(0, 8)}</div>
              <ResultPanel result={selected} />
            </>
          ) : (
            <Card>
              <EmptyBlock title="Rapor seçilmedi" description="Soldaki listeden bir rapor açarak detayları görüntüleyin." />
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
