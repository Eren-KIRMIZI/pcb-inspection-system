import { useState, type ChangeEvent, type FormEvent } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { inspectImage, mediaUrl } from './api'
import type { InspectionResult } from './types'

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [referenceName, setReferenceName] = useState('')
  const [result, setResult] = useState<InspectionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null)
    setError(null)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) return

    setLoading(true)
    setError(null)
    try {
      setResult(await inspectImage(file, referenceName.trim() || undefined))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Beklenmeyen hata')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result
    ? Object.entries(result.counts).map(([name, count]) => ({ name, count }))
    : []

  return (
    <main className="app">
      <header className="app-header">
        <h1>PCB Inspection System</h1>
        <p>Fotoğraf tabanlı, yapay zekâ destekli kart kalite kontrolü</p>
      </header>

      <section className="panel">
        <h2>Yeni Kontrol</h2>
        <form onSubmit={handleSubmit} className="upload-form">
          <input type="file" accept="image/*" onChange={handleFileChange} />
          <input
            type="text"
            placeholder="Referans adı (opsiyonel)"
            value={referenceName}
            onChange={(event) => setReferenceName(event.target.value)}
          />
          <button type="submit" disabled={!file || loading}>
            {loading ? 'Analiz ediliyor…' : 'Analiz Et'}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      {result && (
        <section className="panel result-panel">
          <div className="result-header">
            <h2>Analiz Sonucu</h2>
            <div className="result-badges">
              <span className={`badge badge-${result.verdict.toLowerCase()}`}>
                {result.verdict}
              </span>
              <span className={`badge badge-${result.engine}`}>
                {result.engine === 'mock' ? 'MOCK MOTOR' : 'GERÇEK MODEL'}
              </span>
            </div>
          </div>

          <div className="decision-reasons">
            <h3>Karar Gerekçesi</h3>
            <ul>
              {result.decision.reasons.map((reason, index) => (
                <li key={`${reason.code}-${index}`} className={`reason-${reason.severity}`}>
                  <strong>{reason.code}</strong> · {reason.message}
                </li>
              ))}
            </ul>
          </div>

          <div className="result-grid">
            <div>
              <h3>İşaretli Görüntü</h3>
              {mediaUrl(result.annotated_image_path) ? (
                <img
                  className="annotated-image"
                  src={mediaUrl(result.annotated_image_path)!}
                  alt="İşaretli PCB görüntüsü"
                />
              ) : (
                <p className="muted">Görüntü oluşturulamadı.</p>
              )}
            </div>

            <div>
              <h3>Kusur Dağılımı</h3>
              {chartData.length > 0 ? (
                <div className="chart">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#ef4444" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="muted">Kusur bulunamadı.</p>
              )}
            </div>
          </div>

          <h3>Tespit Edilen Kusurlar</h3>
          {result.defects.length > 0 ? (
            <table className="defect-table">
              <thead>
                <tr>
                  <th>Sınıf</th>
                  <th>Güven</th>
                  <th>Kutu (x1, y1, x2, y2)</th>
                </tr>
              </thead>
              <tbody>
                {result.defects.map((defect, index) => (
                  <tr key={`${defect.class_name}-${index}`}>
                    <td>{defect.class_name}</td>
                    <td>{(defect.confidence * 100).toFixed(1)}%</td>
                    <td>{defect.bbox.map((value) => value.toFixed(0)).join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">Kusur bulunamadı.</p>
          )}
        </section>
      )}

      {result?.reference_check && (
        <section className="panel">
          <div className="result-header">
            <h2>Referans Kontrolü</h2>
            <span className="badge badge-reference">{result.reference_check.reference}</span>
          </div>
          <p className="muted">
            Hizalama: {result.reference_check.aligned ? 'başarılı' : 'yok'} · Beklenen:{' '}
            {result.reference_check.expected_count} · Eşleşen:{' '}
            {result.reference_check.matched_count} · Ham tespit:{' '}
            {result.reference_check.raw_component_detections} · Eşik üstü:{' '}
            {result.reference_check.qualified_component_detections}
          </p>
          <p className="muted">
            Eksik: {result.reference_check.missing_count} · Yanlış:{' '}
            {result.reference_check.wrong_count} · Kaymış:{' '}
            {result.reference_check.shifted_count} · Fazla:{' '}
            {result.reference_check.extra_count}
          </p>

          {result.reference_check.issues.length > 0 ? (
            <table className="defect-table">
              <thead>
                <tr>
                  <th>Ref</th>
                  <th>Beklenen</th>
                  <th>Sorun</th>
                  <th>Tespit edilen</th>
                  <th>Mesafe</th>
                </tr>
              </thead>
              <tbody>
                {result.reference_check.issues.map((issue, index) => (
                  <tr key={`${issue.ref}-${index}`}>
                    <td>{issue.ref}</td>
                    <td>{issue.expected_type}</td>
                    <td>{issue.issue}</td>
                    <td>{issue.detected_type ?? '—'}</td>
                    <td>{issue.distance_px != null ? `${issue.distance_px} px` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Referansla uyumlu, uyuşmazlık bulunamadı.</p>
          )}
        </section>
      )}
    </main>
  )
}

export default App
