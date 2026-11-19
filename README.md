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

## Yerel Kurulum

Python 3.11+ ve Node.js 20+ önerilir.

```powershell
# Backend (proje kökünden)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000
```

```powershell
# Frontend (ayrı terminal)
cd frontend
npm.cmd install
npm.cmd run dev
```

Arayüz: http://localhost:5173 · API docs: http://localhost:8000/docs

Testler:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Model ağırlığı hazır olduğunda kök dizinde bir `.env` dosyası oluşturulur:

```env
MODEL_PATH=models/pcb-solder-defect-detection-yolo26/best.pt
USE_MOCK_DETECTOR=false
DEVICE=cpu
CONF_THRESHOLD=0.25
```

Model ağırlığı yoksa sistem otomatik olarak mock detector ile çalışır; akış uçtan uca test edilebilir. Veri setleri ve model dosyaları `.gitignore` ile repo dışında tutulur.
