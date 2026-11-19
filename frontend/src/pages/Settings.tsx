import { useEffect, useState } from 'react'
import { getSettings } from '../api'
import type { SettingsResponse } from '../types'
import { Card, ErrorBlock, LoadingBlock, PageHeader } from '../components/ui'

export function Settings() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch((err) => setError(err instanceof Error ? err.message : 'Ayarlar yüklenemedi'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page">
      <PageHeader
        eyebrow="SİSTEM"
        title="Sistem Ayarları"
        description="Etkin yapılandırma .env dosyasından okunur; bu ekran salt okunur."
      />

      {loading && <LoadingBlock label="Yapılandırma okunuyor…" />}
      {error && <ErrorBlock message={error} onRetry={() => window.location.reload()} />}

      {settings && (
        <div className="settings-grid">
          <Card title="Çıkarım Motoru">
            <dl className="settings-list">
              <div><dt>Motor</dt><dd>{settings.engine === 'real' ? 'Gerçek YOLO' : 'Mock'}</dd></div>
              <div><dt>Cihaz</dt><dd>{settings.device}</dd></div>
              <div><dt>Kusur modeli</dt><dd className="mono">{settings.defect_model}</dd></div>
              <div><dt>Komponent modeli</dt><dd className="mono">{settings.component_model ?? 'yok'}</dd></div>
              <div><dt>Sınıf eşikleri</dt><dd>{settings.class_thresholds_applied ? 'thresholds.json uygulandı' : 'uygulanmadı'}</dd></div>
              <div><dt>Genel güven eşiği</dt><dd>{settings.conf_threshold}</dd></div>
            </dl>
          </Card>

          <Card title="Referans Karşılaştırma">
            <dl className="settings-list">
              <div><dt>Min. komponent güveni</dt><dd>{settings.reference_component_min_confidence}</dd></div>
              <div><dt>Eşleştirme mesafe oranı</dt><dd>{settings.reference_match_distance_ratio}</dd></div>
              <div><dt>Kayma mesafe oranı</dt><dd>{settings.reference_shift_distance_ratio}</dd></div>
              <div><dt>Komponent güven eşiği</dt><dd>{settings.component_conf_threshold}</dd></div>
              <div><dt>Komponent görüntü boyutu</dt><dd>{settings.component_imgsz} px</dd></div>
            </dl>
          </Card>

          <Card title="Görüntü Doğrulama">
            <dl className="settings-list">
              <div><dt>Min. genişlik</dt><dd>{settings.min_image_width} px</dd></div>
              <div><dt>Min. yükseklik</dt><dd>{settings.min_image_height} px</dd></div>
              <div><dt>Maks. dosya boyutu</dt><dd>{settings.max_upload_mb} MB</dd></div>
              <div><dt>EXIF yönü</dt><dd>uygulanıyor</dd></div>
              <div><dt>Desteklenen formatlar</dt><dd>JPG, PNG, BMP, WEBP</dd></div>
            </dl>
          </Card>
        </div>
      )}
    </div>
  )
}
