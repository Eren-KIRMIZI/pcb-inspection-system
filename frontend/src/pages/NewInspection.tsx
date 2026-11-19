import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react'
import { getReferences, inspectImage } from '../api'
import type { InspectionResult, ReferenceSummary } from '../types'
import { PcbViewer } from '../components/PcbViewer'
import { ResultPanel } from '../components/ResultPanel'
import {
  Card,
  ErrorBlock,
  Icon,
  PageHeader,
  StatCard,
  formatDuration,
} from '../components/ui'

export function NewInspection({
  result,
  onResult,
  initialReference,
}: {
  result: InspectionResult | null
  onResult: (result: InspectionResult | null) => void
  initialReference?: string
}) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [references, setReferences] = useState<ReferenceSummary[]>([])
  const [referenceName, setReferenceName] = useState(initialReference ?? '')
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    getReferences()
      .then(setReferences)
      .catch(() => setReferences([]))
  }, [])

  useEffect(() => {
    if (initialReference) setReferenceName(initialReference)
  }, [initialReference])

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview) }
  }, [preview])

  const chooseFile = (next: File | null) => {
    if (preview) URL.revokeObjectURL(preview)
    setFile(next)
    setPreview(next ? URL.createObjectURL(next) : null)
    setError(null)
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragOver(false)
    chooseFile(event.dataTransfer.files?.[0] ?? null)
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const created = await inspectImage(file, referenceName.trim() || undefined)
      onResult(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analiz başarısız oldu')
      onResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="KONTROL İSTASYONU"
        title="Yeni PCB Analizi"
        description="PCB fotoğrafını yükleyin, isteğe bağlı referans seçin ve kalite kararını alın."
      />

      <div className="inspection-layout">
        <Card title="1 · Görüntü ve Ayarlar" className="inspection-setup">
          <form onSubmit={submit} className="inspection-form">
            <div
              className={`dropzone ${dragOver ? 'dropzone-active' : ''}`}
              onDragOver={(event) => { event.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click()
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept="image/jpeg,image/png,image/bmp,image/webp"
                hidden
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  chooseFile(event.target.files?.[0] ?? null)
                }
              />
              {preview ? (
                <div className="preview">
                  <img src={preview} alt="Yüklenecek PCB" />
                  <span className="preview-name">{file?.name}</span>
                  <span className="preview-change">Değiştirmek için tıklayın</span>
                </div>
              ) : (
                <div className="dropzone-empty">
                  <Icon name="upload" size={30} />
                  <strong>PCB görüntüsünü sürükleyin</strong>
                  <span>veya seçmek için tıklayın</span>
                  <small>JPG, PNG, BMP, WEBP · en fazla 20 MB</small>
                </div>
              )}
            </div>

            <label className="field">
              <span>Referans kart (opsiyonel)</span>
              <select
                className="select"
                value={referenceName}
                onChange={(event) => setReferenceName(event.target.value)}
              >
                <option value="">Referans kullanma</option>
                {references.map((reference) => (
                  <option key={reference.name} value={reference.name}>
                    {reference.name} · {reference.component_count} komponent
                  </option>
                ))}
              </select>
              <small>Seçilirse eksik, yanlış, kaymış ve fazla komponent kontrolü yapılır.</small>
            </label>

            <button type="submit" className="btn btn-primary btn-block" disabled={!file || loading}>
              {loading ? (
                <><span className="spinner spinner-sm" /> Analiz ediliyor…</>
              ) : (
                <><Icon name="shield" size={17} /> Analizi Başlat</>
              )}
            </button>

            {loading && (
              <div className="progress-note">
                <span className="progress-bar" />
                Görüntü işleniyor; CPU üzerinde çıkarım birkaç saniye sürebilir.
              </div>
            )}
            {error && <ErrorBlock message={error} />}
          </form>
        </Card>

        <Card title="2 · PCB Görüntüleyici" subtitle="Yakınlaştırma, kaydırma, kutu filtreleme ve detay inceleme" className="inspection-viewer">
          {result ? <PcbViewer result={result} /> : (
            <div className="viewer-empty">
              <Icon name="image" size={34} />
              <strong>Henüz analiz yok</strong>
              <p className="muted">Bir görüntü yükleyip analizi başlattığınızda işaretli PCB burada görünür.</p>
            </div>
          )}
        </Card>
      </div>

      {result && (
        <>
          <div className="stat-grid compact">
            <StatCard label="Kusur sayısı" value={result.defects.length} hint="eşik üstü tespit" tone={result.defects.length ? 'fail' : 'pass'} />
            <StatCard label="Analiz süresi" value={formatDuration(result.duration_ms)} hint={result.model.device} tone="info" />
            <StatCard
              label="Referans"
              value={result.reference_check ? `${result.reference_check.matched_count}/${result.reference_check.expected_count}` : '—'}
              hint={result.reference_check ? `${result.reference_check.reference} eşleşen` : 'kullanılmadı'}
              tone="info"
            />
            <StatCard label="Görüntü" value={`${result.image_width}×${result.image_height}`} hint="piksel" tone="default" />
          </div>
          <ResultPanel result={result} />
        </>
      )}
    </div>
  )
}
