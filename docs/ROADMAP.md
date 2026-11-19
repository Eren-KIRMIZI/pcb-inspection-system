# Yol Haritası ve Commit Planı

Her tamamlanan adım commit edilip remote'a push edilir.

| # | Adım | Önerilen commit mesajı |
| --- | --- | --- |
| 1 | Repo iskeleti, dokümanlar, veri seti araştırması | `chore: initialize project and dataset research` |
| 2 | Backend iskeleti: FastAPI, config, şema modelleri | `feat: scaffold FastAPI backend` |
| 3 | Görüntü yükleme ve depolama servisi | `feat: add image upload service` |
| 4 | YOLO çıkarım servisi ve sonuç şeması | `feat: add YOLO inference service` |
| 5 | Analiz endpoint'i: `/api/v1/inspections` | `feat: add inspection API endpoint` |
| 6 | Frontend iskeleti: React + TypeScript + Vite | `feat: scaffold React dashboard` |
| 7 | Yükleme ekranı, işaretli görüntü ve kusur tablosu | `feat: add analysis result view` |
| 8 | Karar motoru: PASS / FAIL / MANUAL REVIEW | `feat: add quality decision engine` |
| 9 | Referans/BOM karşılaştırma katmanı | `feat: add reference comparison` |
| 10 | JSON + PDF rapor çıktısı | `feat: add inspection reports` |
| 11 | Temel testler ve CI | `test: add pipeline tests` |
| 12 | Sağlamlaştırma: EXIF, kilitli model yükleyici, hizalama kararı, genişletilmiş testler | `fix: harden inspection pipeline and decision traceability` |
| 13 | Geçmiş/istatistik API'si, model/ayar/referans endpoint'leri, SQLite kayıt | `feat: add inspection history, overview stats and system endpoints` |
| 14 | Endüstriyel koyu tema, hash router, 7 sayfa, zoom/pan görüntüleyici | `feat: add industrial AOI dashboard and inspection workspace` |
| 15 | Ortak hata şeması, `X-Request-ID`, yapılandırılmış JSON log | `feat: add structured logging and standard API errors` |
| 16 | (Sonraki) Eşleştirme iyileştirmeleri, tiling/SAHI, gerçek metrik değerlendirmesi | `feat: improve reference matching and evaluation` |

## Aşama 1 tanımı (MVP) — tamamlandı

- Kullanıcı bir PCB fotoğrafı yükler.
- Backend görüntüyü YOLO modeliyle analiz eder.
- Kusurlar görüntü üzerinde işaretlenir ve tabloya dökülür.
- Karar motoru gerekçeli PASS / FAIL / MANUAL REVIEW üretir; referans/BOM sonucu karara girer.
- Sonuç JSON olarak döner, arayüzde gösterilir ve SQLite geçmişine kaydedilir.
- JSON/PDF rapor indirilebilir; ana sayfa gerçek KPI ve trend grafikleri gösterir.

## Aşama 2 tanımı (arayüz) — tamamlandı

- Industrial Dark tema, sidebar ve hash tabanlı 7 sayfa (geçmiş, referans, raporlar, model performansı, ayarlar).
- Görüntüleyici: zoom/pan/fit, orijinal/işaretli geçişi, sınıf filtresi, kutu detayı.
- Model ekranı yalnızca model kartındaki doğrulanmış metrikleri gösterir; uydurma precision/recall yok.

## Aşama 3 tanımı (izlenebilirlik) — tamamlandı

- Tüm hata yanıtları `{error, detail, request_id}` gövdesini ve `X-Request-ID` başlığını kullanır.
- Tek satırlık JSON log; istek ve analiz olayları aynı `request_id` ile korele edilir.
- `LOG_LEVEL` ortam değişkeniyle log seviyesi ayarlanabilir.

Kamera, canlı görüntü, donanım kalibrasyonu, lokal model eğitimi ve containerization bu sürümde yoktur.
