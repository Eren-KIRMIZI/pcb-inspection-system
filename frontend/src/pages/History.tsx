import { useCallback, useEffect, useState } from 'react'
import { getHistory } from '../api'
import type { HistoryEntry } from '../types'
import {
  EmptyBlock,
  ErrorBlock,
  Icon,
  LoadingBlock,
  PageHeader,
  VerdictBadge,
  formatDateTime,
  formatDuration,
} from '../components/ui'

type SortKey = 'newest' | 'oldest' | 'defects' | 'duration'

export function History({ onOpenInspection }: { onOpenInspection: (id: string) => void }) {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [search, setSearch] = useState('')
  const [verdict, setVerdict] = useState('')
  const [engine, setEngine] = useState('')
  const [sort, setSort] = useState<SortKey>('newest')
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (nextOffset = 0, append = false) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getHistory({
        limit: 30,
        offset: nextOffset,
        search: search.trim() || undefined,
        verdict: verdict || undefined,
        engine: engine || undefined,
      })
      setEntries((current) => (append ? [...current, ...data] : data))
      setOffset(nextOffset + data.length)
      setHasMore(data.length === 30)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Geçmiş yüklenemedi')
    } finally {
      setLoading(false)
    }
  }, [search, verdict, engine])

  useEffect(() => {
    void load(0, false)
  }, [load])

  const sorted = [...entries].sort((a, b) => {
    if (sort === 'newest') return b.created_at.localeCompare(a.created_at)
    if (sort === 'oldest') return a.created_at.localeCompare(b.created_at)
    if (sort === 'defects') return b.defect_count - a.defect_count
    return b.duration_ms - a.duration_ms
  })

  return (
    <div className="page">
      <PageHeader
        eyebrow="KAYITLAR"
        title="Analiz Geçmişi"
        description="Kaydedilen tüm analizler; filtreleyin, sıralayın ve detaya gidin."
      />

      <div className="card">
        <div className="filter-bar">
          <label className="search-field">
            <Icon name="search" size={16} />
            <input
              type="search"
              placeholder="Dosya adı veya analiz ID"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <select className="select" value={verdict} onChange={(event) => setVerdict(event.target.value)} aria-label="Karar filtresi">
            <option value="">Tüm kararlar</option>
            <option value="PASS">PASS</option>
            <option value="FAIL">FAIL</option>
            <option value="MANUAL_REVIEW">MANUEL İNCELEME</option>
          </select>
          <select className="select" value={engine} onChange={(event) => setEngine(event.target.value)} aria-label="Motor filtresi">
            <option value="">Tüm motorlar</option>
            <option value="real">Gerçek model</option>
            <option value="mock">Mock</option>
          </select>
          <select className="select" value={sort} onChange={(event) => setSort(event.target.value as SortKey)} aria-label="Sıralama">
            <option value="newest">En yeni</option>
            <option value="oldest">En eski</option>
            <option value="defects">En çok kusur</option>
            <option value="duration">En uzun süre</option>
          </select>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load(0, false)}>
            <Icon name="fit" size={14} /> Yenile
          </button>
        </div>

        {loading && entries.length === 0 && <LoadingBlock label="Kayıtlar alınıyor…" />}
        {error && <ErrorBlock message={error} onRetry={() => void load(0, false)} />}

        {!loading && !error && sorted.length === 0 && (
          <EmptyBlock
            title="Kayıt bulunamadı"
            description="Filtreleri değiştirin veya yeni bir analiz başlatın."
          />
        )}

        {sorted.length > 0 && (
          <>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Analiz ID</th>
                    <th>Dosya</th>
                    <th>Karar</th>
                    <th>Kusur</th>
                    <th>Referans</th>
                    <th>Süre</th>
                    <th>Tarih</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((entry) => (
                    <tr key={entry.image_id} className="clickable-row" onClick={() => onOpenInspection(entry.image_id)}>
                      <td className="mono">{entry.image_id.slice(0, 8)}</td>
                      <td title={entry.filename}>{entry.filename}</td>
                      <td><VerdictBadge verdict={entry.verdict} /></td>
                      <td>{entry.defect_count}</td>
                      <td>{entry.reference_name ?? '—'}</td>
                      <td>{formatDuration(entry.duration_ms)}</td>
                      <td>{formatDateTime(entry.created_at)}</td>
                      <td><Icon name="chevron" size={15} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-footer">
              <span className="muted">{sorted.length} kayıt gösteriliyor</span>
              {hasMore && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load(offset, true)} disabled={loading}>
                  Daha fazla yükle
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
