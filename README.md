# PCB Inspection System

Fotoğraf tabanlı, yapay zekâ destekli PCB kalite kontrol sistemi.

## Kararlar

- **Donanım yok:** Sistem yalnızca yüklenen PCB fotoğraflarıyla çalışır.
- **Kamera entegrasyonu plan dışıdır.** Gerekirse ileride ayrı bir `ImageSource` olarak eklenebilir; mevcut mimariyi değiştirmez.
- **Gerçek AOI yaklaşımı:** Tek bir YOLO kutusu çizmek yerine tespit → karar motoru → rapor akışı kurulur.

## Kapsam

1. Eksik komponent tespiti (referans/BOM karşılaştırmasıyla)
2. Yanlış yerleşim / kaymış komponent tespiti
3. Lehim kusurları: köprü, yetersiz/fazla lehim (`solder_void` düşük güvenilirliktedir; RGB fotoğrafta lehim altı void güvenilir biçimde doğrulanamaz)
4. Referans kart / BOM karşılaştırması — [`docs/REFERENCE.md`](docs/REFERENCE.md)

Desteklenmeyen: `rotation_error` (komponent modeli açı üretmez), `open_joint` (model sınıfı yok), bilinmeyen anomali (anomaly detection modeli yok). Ayrıntılar: [`docs/MODELS.md`](docs/MODELS.md).

Çıktılar: işaretlenmiş görüntü, kusur listesi, gerekçeli `PASS / FAIL / MANUAL REVIEW` kararı, JSON/PDF rapor, SQLite geçmiş kaydı.

## Teknoloji yığını

| Katman | Teknoloji |
| --- | --- |
| AI / CV | Python, PyTorch (CPU), Ultralytics YOLO26, OpenCV (SIFT + RANSAC hizalama) |
| Backend | FastAPI, Pydantic, `sqlite3` (stdlib) |
| Frontend | React + TypeScript, Vite, Recharts, hash tabanlı router |
| Loglama | Tek satırlık JSON, `request_id` korelasyonu, `LOG_LEVEL` |
| Veri | Yerel dosya sistemi + `data/inspections.db` (çok kullanıcılı aşamada PostgreSQL) |

Yerel model eğitimi yoktur; yalnızca hazır `.pt` ağırlıkları kullanılır.

## Aşamalar

- **Aşama 1 — güvenilirlik ve karar motoru:** gerçek YOLO çıkarımı, sınıf eşikleri, referans eşleştirme, gerekçeli karar, mock/gerçek ayrımı, görüntü doğrulama, kilitli model yükleyici, hata şeması, testler. ✅
- **Aşama 2 — arayüz:** Industrial Dark tema, 7 sayfalık hash router, zoom/pan görüntüleyici, geçmiş/raporlar, gerçek metriklerle model ekranı. ✅
- **Aşama 3 — operasyonel izlenebilirlik:** ortak API hata gövdesi, `X-Request-ID`, yapılandırılmış JSON log. ✅
- **Sonraki:** one-to-one eşleştirme iyileştirmeleri, tiling/SAHI, gerçek metrik değerlendirmesi, çok kullanıcılı veri katmanı. Kamera/donanım bu sürümde yoktur.

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

Üretim derlemesi:

```powershell
cd frontend
npm.cmd run build
```

Testler:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

## API ve hata şeması

Ana endpoint'ler: `POST /api/v1/uploads`, `POST /api/v1/inspections`, `GET /api/v1/history`,
`GET /api/v1/history/overview`, `GET /api/v1/history/{id}`, `GET /api/v1/references`,
`GET /api/v1/models`, `GET /api/v1/settings`.

Tüm hata yanıtları aynı gövdeyi kullanır ve `X-Request-ID` başlığı taşır:

```json
{
  "error": "bad_request",
  "detail": "Dosya geçerli bir görüntü değil",
  "request_id": "verify-i3-001"
}
```

İstekte `X-Request-ID` gönderilirse aynı değer yansıtılır; aksi halde sunucu UUID üretir.
Her istek ve analiz tek satırlık JSON olarak loglanır; `request_id` alanı logları istekle
iliştirir. Log seviyesi `.env` içindeki `LOG_LEVEL` ile ayarlanır (varsayılan `INFO`).
Önemli olaylar: `request_completed`, `api_error`, `validation_error`, `inspection_completed`.

Hazır modeli indir (lokal eğitim gerekmez):

```powershell
.\.venv\Scripts\python.exe -m backend.training.download_model
Copy-Item .env.example .env
```

`.env` içeriği hazır modeli ve sınıf bazlı eşikleri gösterir. GPU varsa `DEVICE=0`, yoksa `DEVICE=cpu` kullanın. Ayrıntılar: [`docs/MODELS.md`](docs/MODELS.md)

Model dosyası yoksa sistem otomatik olarak mock detector ile çalışır; akış uçtan uca test edilebilir, ancak mock motor asla `PASS` kararı vermez ve sonuç `MANUAL_REVIEW` olarak işaretlenir. Veri setleri, model dosyaları, `data/` altındaki yüklemeler/raporlar/SQLite veritabanı `.gitignore` ile repo dışında tutulur; denetim geçmişi ve teknik bulgular [`docs/AUDIT.md`](docs/AUDIT.md) içindedir.
