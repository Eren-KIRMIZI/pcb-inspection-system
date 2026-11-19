import { useEffect, useState } from 'react'
import { getModels } from '../api'
import { defectLabel } from '../labels'
import type { ModelPerformance as ModelPerformanceData } from '../types'
import {
  Card,
  ErrorBlock,
  Icon,
  LoadingBlock,
  PageHeader,
} from '../components/ui'

const STATUS_LABEL = {
  active: 'Aktif',
  configured: 'Yapılandırıldı',
  disabled: 'Kapalı',
} as const

const percent = (value: number) => `%${(value * 100).toFixed(1)}`

export function ModelPerformance() {
  const [data, setData] = useState<ModelPerformanceData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getModels()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Model bilgisi yüklenemedi'))
      .finally(() => setLoading(false))
  }, [])

  const evaluation = data?.measured_in_app ? data.evaluation : null

  return (
    <div className="page">
      <PageHeader
        eyebrow="MODEL YÖNETİMİ"
        title="Model Performansı"
        description="Hazır model ağırlıklarının belgelenmiş metrikleri, uygulama içi ölçüm ve bilinen sınırlar."
      />

      {loading && <LoadingBlock label="Model bilgileri alınıyor…" />}
      {error && <ErrorBlock message={error} onRetry={() => window.location.reload()} />}

      {data && (
        <>
          <div className="notice">
            <Icon name="alert" size={18} />
            <div>
              <strong>Ölçüm kaynağı</strong>
              <p>
                {evaluation
                  ? `Kart metrikleri model kartındaki ayrılmış test setine aittir. Kusur modeli ayrıca bu uygulamada gerçek test split'i (${evaluation.image_count} görsel / ${evaluation.ground_truth_boxes} kutu) üzerinden ölçülmüştür; precision, recall, F1, AP ve sınıf bazlı sonuçlar aşağıdadır.`
                  : 'Aşağıdaki mAP değerleri model kartlarındaki ayrılmış test seti sonuçlarıdır; bu uygulama içinde yeniden ölçülmemiştir. Uygulama içi değerlendirme yapılmadığı için precision, recall ve confusion matrix gibi metrikler gösterilmez.'}
              </p>
            </div>
          </div>

          {evaluation && (
            <Card
              title="Uygulama İçi Ölçüm"
              subtitle={`${evaluation.model_name} · ${evaluation.split} split'i · ${new Date(evaluation.evaluated_at).toLocaleString('tr-TR')}`}
            >
              <div className="metric-row">
                <div className="metric"><span>Precision</span><strong>{percent(evaluation.overall.precision)}</strong></div>
                <div className="metric"><span>Recall</span><strong>{percent(evaluation.overall.recall)}</strong></div>
                <div className="metric"><span>F1</span><strong>{percent(evaluation.overall.f1)}</strong></div>
                <div className="metric"><span>mAP50</span><strong>{evaluation.overall.ap50.toFixed(3)}</strong></div>
                <div className="metric"><span>mAP50-95</span><strong>{evaluation.overall.ap50_95.toFixed(3)}</strong></div>
              </div>
              <p className="source-line">
                {evaluation.device} · imgsz {evaluation.imgsz} · sınıf eşikleri {evaluation.class_thresholds_applied ? 'uygulandı' : 'uygulanmadı'} · güven {evaluation.conf_threshold} · {evaluation.mean_inference_ms.toFixed(1)} ms/görsel
              </p>
              <p className="muted">
                TP {evaluation.overall.tp} · FP {evaluation.overall.fp} · FN {evaluation.overall.fn} · tahmin edilen kutu {evaluation.predicted_boxes}
              </p>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Sınıf</th>
                      <th>Destek</th>
                      <th>Precision</th>
                      <th>Recall</th>
                      <th>F1</th>
                      <th>AP50</th>
                      <th>AP50-95</th>
                      <th>TP / FP / FN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evaluation.classes.map((item) => (
                      <tr key={item.class_name}>
                        <td>{defectLabel(item.class_name)}</td>
                        <td className="mono">{item.support}</td>
                        <td className="mono">{item.support > 0 ? percent(item.precision) : '—'}</td>
                        <td className="mono">{item.support > 0 ? percent(item.recall) : '—'}</td>
                        <td className="mono">{item.support > 0 ? percent(item.f1) : '—'}</td>
                        <td className="mono">{item.support > 0 ? item.ap50.toFixed(3) : '—'}</td>
                        <td className="mono">{item.support > 0 ? item.ap50_95.toFixed(3) : '—'}</td>
                        <td className="mono">{item.tp} / {item.fp} / {item.fn}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {evaluation.classes_without_ground_truth.length > 0 && (
                <p className="muted">
                  Test split'inde ground truth bulunmayan sınıflar (mAP ortalamasına dahil edilmez):{' '}
                  {evaluation.classes_without_ground_truth.map(defectLabel).join(', ')}.
                </p>
              )}
            </Card>
          )}

          <div className="model-grid">
            {data.models.map((model) => (
              <Card
                key={model.id}
                title={model.name}
                subtitle={model.role}
                actions={<span className={`badge status-${model.status}`}>{STATUS_LABEL[model.status]}</span>}
              >
                <div className="metric-row">
                  <div className="metric">
                    <span>mAP50</span>
                    <strong>{model.map50 != null ? model.map50.toFixed(3) : '—'}</strong>
                  </div>
                  <div className="metric">
                    <span>mAP50-95</span>
                    <strong>{model.map50_95 != null ? model.map50_95.toFixed(3) : '—'}</strong>
                  </div>
                  <div className="metric">
                    <span>Sınıf</span>
                    <strong>{model.classes.length || '—'}</strong>
                  </div>
                </div>
                <p className="source-line">{model.source}</p>
                <p className="muted">{model.note}</p>
                {model.classes.length > 0 && (
                  <div className="class-chips">
                    {model.classes.map((name) => <span key={name} className="class-chip">{name}</span>)}
                  </div>
                )}
              </Card>
            ))}
          </div>

          <div className="dashboard-grid">
            <Card
              title={evaluation ? 'Kalan Ölçülmeyen Metrikler' : 'Ölçülmeyen Metrikler'}
              subtitle="Gerçek değer olmadığı için gösterilmez"
            >
              <ul className="plain-list">
                {data.unmeasured_metrics.map((metric) => (
                  <li key={metric}><Icon name="close" size={14} /> {metric}</li>
                ))}
              </ul>
            </Card>
            <Card title="Bilinen Sınırlar" subtitle="Model kartı ve saha notları">
              <ul className="plain-list warning-list">
                {data.limitations.map((item) => (
                  <li key={item}><Icon name="alert" size={14} /> {item}</li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
