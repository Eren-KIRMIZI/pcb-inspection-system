# PCB Inspection System

Fotoğraf tabanlı, yapay zekâ destekli PCB kalite kontrol sistemi.

## Kararlar

- **Donanım yok:** Sistem yalnızca yüklenen PCB fotoğraflarıyla çalışır.
- **Kamera entegrasyonu plan dışıdır.** Gerekirse ileride ayrı bir `ImageSource` olarak eklenebilir; mevcut mimariyi değiştirmez.
- **Gerçek AOI yaklaşımı:** Tek bir YOLO kutusu çizmek yerine tespit → karar motoru → rapor akışı kurulur.

## Kapsam

1. Eksik komponent tespiti
2. Yanlış yerleşim / kaymış komponent tespiti
3. Lehim kusurları: köprü, yetersiz/fazla lehim, void
4. Referans kart / BOM karşılaştırması (Aşama 2)

Çıktılar: işaretlenmiş görüntü, kusur listesi, `PASS / FAIL / MANUAL REVIEW` kararı, JSON/PDF rapor.

## Teknoloji yığını (plan)

| Katman | Teknoloji |
| --- | --- |
| AI / CV | Python, PyTorch, Ultralytics YOLO, OpenCV |
| Backend | FastAPI |
| Frontend | React + TypeScript, Recharts |
| Veri | PostgreSQL (sonraki aşama), yerel dosya sistemi |
| İleri AI | Anomalib / U-Net (Aşama 2) |

## Aşamalar

- **Aşama 1 — MVP:** fotoğraf yükleme, YOLO çıkarımı, eksik/kaymış komponent ve lehim kusurları, sonuç ekranı, rapor.
- **Aşama 2:** referans/BOM doğrulama, OpenCV hizalama, anomali tespiti, model metrikleri.
- **Aşama 3 (opsiyonel):** üretim istatistikleri ve gelişmiş raporlama. Kamera bu sürümde yoktur.

## Veri setleri

Araştırma ve seçim gerekçesi: [`docs/DATASETS.md`](docs/DATASETS.md)  
Geliştirme planı: [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Geliştirme

Kurulum adımları ilerleyen commit'lerde eklenecek. Veri setleri ve model ağırlıkları repo'ya eklenmeyecektir.
