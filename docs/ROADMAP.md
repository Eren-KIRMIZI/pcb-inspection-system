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
| 16 | Hizalama güveni: SIFT/RANSAC inlier/oran/ölçek/açı, önbellek, MANUAL_REVIEW | `feat: improve PCB image alignment` |
| 17 | Global komponent eşleştirme (Hungarian, maliyet matrisi) | `feat: add component matching engine` |
| 18 | Fark analizi: izlenebilir `extra_component` kimliği | `fix: make extra-component findings traceable` |
| 19 | Rotasyon/konum analizi — kapsam dışı (model açı üretmiyor) | — |
| 20 | Tiling ve `imgsz`/IoU ayarları, sınıf eşikleri korundu | `feat: add tiled defect inference` |
| 21/22 | Gerçek test split'i ile uygulama içi değerlendirme ve sınıf bazlı metrikler | `feat: add in-app model evaluation` |
| 23 | Regresyon: karar eşikleri ve model hata sınıfı | `fix: harden decision thresholds and model errors` |
| — | Dashboard KPI/dönem/sistem durumu düzeltmeleri (D1/D9/D10/D11/D13) | `feat: add period-aware dashboard metrics and system status` |

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
- Model ekranı model kartı metriklerini gösterir; uydurma precision/recall yok. Gerçek ölçüm yapıldıysa ayrı bir panelde sınıf bazlı sonuçlar ve kaynak bilgisiyle birlikte gösterilir.

## Aşama 3 tanımı (izlenebilirlik) — tamamlandı

- Tüm hata yanıtları `{error, detail, request_id}` gövdesini ve `X-Request-ID` başlığını kullanır.
- Tek satırlık JSON log; istek ve analiz olayları aynı `request_id` ile korele edilir.
- `LOG_LEVEL` ortam değişkeniyle log seviyesi ayarlanabilir.

## Aşama 4 tanımı (AOI Engine 2.0) — tamamlandı

- Referans hizalaması güven skoruyla raporlanır; güvenilmez hizalama MANUAL_REVIEW üretir.
- Komponent eşleştirmesi global minimum maliyetle yapılır; fazla komponentler izlenebilir kimlik taşır.
- Tiling varsayılan kapalıdır; açıldığında aynı sınıf eşikleri ve NMS uygulanır.
- Gerçek test split'inde ölçülen metrikler `data/evaluation/*.json` içinde tutulur; `/models` ölçüm yoksa `measured_in_app=false` döner. Model kartı metrikleriyle karıştırılmaz.
- Karar eşikleri ve model hata sınıfları izlenebilir; eksik model 503 döndürür.

Kamera, canlı görüntü, donanım kalibrasyonu, lokal model eğitimi, rotasyon/konum analizi ve containerization bu sürümde yoktur.
