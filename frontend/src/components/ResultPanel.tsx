import { downloadUrl } from '../api'
import { defectLabel, issueLabel } from '../labels'
import type { InspectionResult } from '../types'
import {
  Card,
  EngineBadge,
  Icon,
  SeverityPill,
  VerdictBadge,
  formatDateTime,
  formatDuration,
} from './ui'

export function DecisionReasons({ result }: { result: InspectionResult }) {
  return (
    <Card title="Karar Gerekçesi" subtitle="Kararın hangi bulgulara dayandığını gösterir">
      <ul className="reason-list">
        {result.decision.reasons.map((reason, index) => (
          <li key={`${reason.code}-${index}`} className={`reason-item reason-${reason.severity}`}>
            <SeverityPill severity={reason.severity} />
            <div>
              <strong>{reason.code}</strong>
              <span>{reason.message}</span>
            </div>
            <span className="reason-source">{reason.source}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function DefectTable({ result }: { result: InspectionResult }) {
  if (result.defects.length === 0) {
    return <p className="muted">Kusur tespit edilmedi.</p>
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
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
              <td>
                <span className="class-tag">{defectLabel(defect.class_name)}</span>
                <small className="mono raw-class">{defect.class_name}</small>
              </td>
              <td>
                <div className="confidence">
                  <span>%{ (defect.confidence * 100).toFixed(1) }</span>
                  <span className="confidence-track">
                    <span style={{ width: `${defect.confidence * 100}%` }} />
                  </span>
                </div>
              </td>
              <td className="mono">{defect.bbox.map((value) => value.toFixed(0)).join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ReferenceSection({ result }: { result: InspectionResult }) {
  const check = result.reference_check
  if (!check) {
    return (
      <Card title="Referans Kontrolü">
        <p className="muted">
          Bu analizde referans/BOM karşılaştırması yapılmadı. Eksik komponent değerlendirilemedi.
        </p>
      </Card>
    )
  }

  const alignment = check.alignment
  const alignmentDetail = alignment
    ? `Ref: ${check.reference} · Hizalama: ${check.aligned ? 'güvenilir' : 'güvenilmez'} · ` +
      `inlier %${(alignment.inlier_ratio * 100).toFixed(0)} (${alignment.inlier_count}) · ` +
      `ölçek ${alignment.scale?.toFixed(2) ?? '—'} · neden: ${alignment.reason}`
    : `Ref: ${check.reference} · Hizalama: ${check.aligned ? 'başarılı' : 'başarısız'}`
  const matching = check.matching
  const matchingDetail = matching
    ? ` · eşleştirme: ${matching.algorithm}, ${matching.assignments} atama, ` +
      `maliyet ${matching.cost_total.toFixed(2)}`
    : ''

  return (
    <Card
      title="Referans / BOM Kontrolü"
      subtitle={alignmentDetail + matchingDetail}
    >
      <div className="mini-stats">
        <div><span>Beklenen</span><strong>{check.expected_count}</strong></div>
        <div><span>Eşleşen</span><strong>{check.matched_count}</strong></div>
        <div><span>Ham tespit</span><strong>{check.raw_component_detections}</strong></div>
        <div><span>Eşik üstü</span><strong>{check.qualified_component_detections}</strong></div>
        <div><span>Eksik</span><strong className={check.missing_count ? 'text-fail' : ''}>{check.missing_count}</strong></div>
        <div><span>Yanlış</span><strong className={check.wrong_count ? 'text-fail' : ''}>{check.wrong_count}</strong></div>
        <div><span>Kaymış</span><strong className={check.shifted_count ? 'text-fail' : ''}>{check.shifted_count}</strong></div>
        <div><span>Fazla</span><strong className={check.extra_count ? 'text-fail' : ''}>{check.extra_count}</strong></div>
      </div>

      {check.issues.length > 0 ? (
        <div className="table-scroll">
          <table className="data-table">
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
              {check.issues.map((issue, index) => (
                <tr key={`${issue.ref}-${index}`}>
                  <td className="mono">{issue.ref}</td>
                  <td>{issue.expected_type}</td>
                  <td><span className="issue-tag">{issueLabel(issue.issue)}</span></td>
                  <td>{issue.detected_type ?? '—'}</td>
                  <td className="mono">{issue.distance_px != null ? `${issue.distance_px} px` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="success-line"><Icon name="check" size={15} /> Referansla uyumlu, uyuşmazlık bulunamadı.</p>
      )}
    </Card>
  )
}

export function ResultPanel({ result }: { result: InspectionResult }) {
  const reportLinks = [
    result.report_json_path && { label: 'JSON raporu', url: downloadUrl(result.report_json_path) },
    result.report_pdf_path && { label: 'PDF raporu', url: downloadUrl(result.report_pdf_path) },
  ].filter(Boolean) as Array<{ label: string; url: string }>

  return (
    <div className="result-stack">
      <section className={`verdict-banner verdict-banner-${result.verdict.toLowerCase()}`}>
        <div className="verdict-main">
          <span className="verdict-caption">NİHAİ KARAR</span>
          <VerdictBadge verdict={result.verdict} />
          <EngineBadge engine={result.engine} />
        </div>
        <div className="verdict-meta">
          <div><span>Analiz ID</span><strong className="mono">{result.image_id.slice(0, 8)}…</strong></div>
          <div><span>Dosya</span><strong title={result.filename}>{result.filename}</strong></div>
          <div><span>Tarih</span><strong>{formatDateTime(result.created_at)}</strong></div>
          <div><span>Süre</span><strong>{formatDuration(result.duration_ms)}</strong></div>
          <div><span>Görüntü</span><strong>{result.image_width}×{result.image_height}</strong></div>
        </div>
        {reportLinks.length > 0 && (
          <div className="verdict-links">
            {reportLinks.map((link) => (
              <a key={link.label} className="btn btn-ghost btn-sm" href={link.url} download>
                <Icon name="download" size={15} /> {link.label}
              </a>
            ))}
          </div>
        )}
      </section>

      <DecisionReasons result={result} />
      <ReferenceSection result={result} />

      <Card title={`Tespit Edilen Kusurlar (${result.defects.length})`} subtitle="YOLO kusur modelinin sınıf bazlı eşikleri geçen çıktıları">
        <DefectTable result={result} />
      </Card>

      <Card title="Model Bilgisi">
        <div className="model-strip">
          <div><span>Kusur modeli</span><strong>{result.model.defect_model}</strong></div>
          <div><span>Komponent modeli</span><strong>{result.model.component_model ?? 'kullanılmadı'}</strong></div>
          <div><span>Cihaz</span><strong>{result.model.device}</strong></div>
          <div><span>Sınıf eşikleri</span><strong>{result.model.class_thresholds_applied ? 'uygulandı' : 'uygulanmadı'}</strong></div>
        </div>
      </Card>
    </div>
  )
}
