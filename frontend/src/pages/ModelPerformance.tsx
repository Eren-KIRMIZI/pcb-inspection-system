import { useEffect, useState } from 'react'
import { getModels } from '../api'
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

  return (
    <div className="page">
      <PageHeader
        eyebrow="MODEL YÖNETİMİ"
        title="Model Performansı"
        description="Hazır model ağırlıklarının belgelenmiş metrikleri ve bilinen sınırları."
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
                Aşağıdaki mAP değerleri model kartlarındaki ayrılmış test seti sonuçlarıdır; bu uygulama
                içinde yeniden ölçülmemiştir. Uygulama içi değerlendirme yapılmadığı için precision,
                recall ve confusion matrix gibi metrikler gösterilmez.
              </p>
            </div>
          </div>

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
            <Card title="Ölçülmeyen Metrikler" subtitle="Gerçek değer olmadığı için gösterilmez">
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
