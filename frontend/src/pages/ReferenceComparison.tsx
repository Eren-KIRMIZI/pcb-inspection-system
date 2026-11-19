import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { createReference, getReference, getReferences, mediaUrl } from '../api'
import type { ReferenceBoard, ReferenceSummary } from '../types'
import {
  Card,
  EmptyBlock,
  ErrorBlock,
  Icon,
  LoadingBlock,
  PageHeader,
} from '../components/ui'

export function ReferenceComparison({
  onUseReference,
}: {
  onUseReference: (name: string) => void
}) {
  const [references, setReferences] = useState<ReferenceSummary[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [board, setBoard] = useState<ReferenceBoard | null>(null)
  const [componentSearch, setComponentSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [bom, setBom] = useState<File | null>(null)

  const loadReferences = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getReferences()
      setReferences(data)
      setSelected((current) => current ?? data[0]?.name ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Referanslar yüklenemedi')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadReferences() }, [loadReferences])

  useEffect(() => {
    if (!selected) { setBoard(null); return }
    getReference(selected).then(setBoard).catch(() => setBoard(null))
  }, [selected])

  const filtered = (board?.components ?? []).filter((component) =>
    `${component.ref} ${component.type}`.toLowerCase().includes(componentSearch.toLowerCase()),
  )

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!name.trim() || !image || !bom) return
    setCreating(true)
    setFormError(null)
    try {
      const created = await createReference(name.trim(), image, bom)
      await loadReferences()
      setSelected(created.name)
      setName(''); setImage(null); setBom(null)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Referans kaydedilemedi')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="BOM / REFERANS"
        title="Referans Karşılaştırma"
        description="Referans kart listesi, BOM içeriği ve yeni referans kaydı."
      />

      {loading && <LoadingBlock label="Referanslar yükleniyor…" />}
      {error && <ErrorBlock message={error} onRetry={() => void loadReferences()} />}

      <div className="reference-layout">
        <Card title="Kayıtlı Referanslar" subtitle={`${references.length} referans kart`}>
          {!loading && !error && references.length === 0 && (
            <EmptyBlock title="Referans yok" description="Aşağıdan yeni bir referans kartı kaydedin." />
          )}
          <div className="reference-list">
            {references.map((reference) => (
              <button
                type="button"
                key={reference.name}
                className={`reference-item ${selected === reference.name ? 'reference-item-active' : ''}`}
                onClick={() => setSelected(reference.name)}
              >
                <Icon name="layers" size={17} />
                <div>
                  <strong>{reference.name}</strong>
                  <span>{reference.component_count} komponent</span>
                </div>
              </button>
            ))}
          </div>
        </Card>

        <Card title={selected ? `BOM · ${selected}` : 'BOM Detayı'} className="span-2">
          {board ? (
            <>
              {mediaUrl(board.image_path) && (
                <div className="reference-image">
                  <img src={mediaUrl(board.image_path)!} alt={`${board.name} referans kartı`} />
                  <span className="muted">{board.image_path}</span>
                </div>
              )}
              <div className="filter-bar compact">
                <label className="search-field">
                  <Icon name="search" size={15} />
                  <input
                    type="search"
                    placeholder="Ref veya tür ara"
                    value={componentSearch}
                    onChange={(event) => setComponentSearch(event.target.value)}
                  />
                </label>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => onUseReference(board.name)}>
                  Bu referansla analiz yap
                </button>
              </div>
              <div className="table-scroll table-limited">
                <table className="data-table">
                  <thead><tr><th>Ref</th><th>Tür</th><th>X</th><th>Y</th></tr></thead>
                  <tbody>
                    {filtered.map((component) => (
                      <tr key={component.ref}>
                        <td className="mono">{component.ref}</td>
                        <td>{component.type}</td>
                        <td className="mono">{component.x.toFixed(4)}</td>
                        <td className="mono">{component.y.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted footnote">{filtered.length} / {board.components.length} komponent gösteriliyor</p>
            </>
          ) : (
            <EmptyBlock title="Referans seçilmedi" description="Soldan bir referans kartı seçin." />
          )}
        </Card>

        <Card title="Yeni Referans Kaydet" subtitle="Referans görseli + BOM JSON dosyası">
          <form className="reference-form" onSubmit={submit}>
            <label className="field">
              <span>Referans adı</span>
              <input
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="ornek_kart_v1"
                required
              />
            </label>
            <label className="field">
              <span>Referans görseli</span>
              <input
                className="input"
                type="file"
                accept="image/*"
                onChange={(event: ChangeEvent<HTMLInputElement>) => setImage(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            <label className="field">
              <span>BOM dosyası (JSON)</span>
              <input
                className="input"
                type="file"
                accept=".json,application/json"
                onChange={(event: ChangeEvent<HTMLInputElement>) => setBom(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            <button type="submit" className="btn btn-primary btn-block" disabled={creating || !name.trim() || !image || !bom}>
              {creating ? 'Kaydediliyor…' : 'Referansı Kaydet'}
            </button>
            {formError && <ErrorBlock message={formError} />}
            <div className="format-hint">
              <strong>BOM formatı</strong>
              <code>{'{"components": [{"ref": "R1", "type": "resistor", "x": 0.42, "y": 0.31}]}'}</code>
              <small>x ve y değerleri 0–1 arası normalize koordinattır.</small>
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}
