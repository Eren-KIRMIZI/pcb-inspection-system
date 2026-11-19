# Teknik Denetim Raporu

Tarih: 2026-11-19  
Kapsam: mevcut FastAPI + React + YOLO akışı (kod okuma, çalışan servisler üzerinde HTTP doğrulaması, 11 birim/integrasyon testi).  
Amaç: projeyi bir YOLO demosundan güvenilir bir AOI kalite kontrol yazılımına taşımadan önce mevcut durumun şeffaf şekilde kaydedilmesi.

## Doğrulanan ölçüm

| İstek | Sonuç |
| --- | --- |
| `GET :5173/media/results/annotated_….jpg` | `200`, `text/html`, 563 byte |
| `GET :8000/media/results/annotated_….jpg` | `200`, `image/jpeg`, 189.911 byte |
| Tarayıcıdaki demo analizi | HTTP 200, ~13 sn (CPU), 4 `excess_solder`, referans `20/120`, 0 uyuşmazlık |
| `pytest backend/tests -q` | 11 passed |

## Bulgular

### Kritik

| # | Bulgu | Yer | Etki |
| --- | --- | --- | --- |
| C1 | **İşaretli görüntü dev ortamında hiç yüklenmiyor.** Vite proxy yalnızca `/api`’yı yönlendiriyor; `/media` isteği SPA’ya düşüp `index.html` dönüyor. | `frontend/vite.config.ts:8-10` | Kalite kontrolünün en önemli görsel çıktısı kullanılamıyor. Backend tarafı sağlam; testler API’ye doğrudan bastığı için hatayı yakalayamamış. |
| C2 | **Referans sonucu kararı etkilemiyor.** `reference_check` hesaplanıp sonuca ekleniyor ama `decide()` yalnızca YOLO kusurlarını görüyor. Eksik/wrong/shifted komponent olsa bile `verdict` PASS kalabiliyor. | `backend/app/routers/inspections.py:21-31`, `services/decision.py:11` | Referans/BOM katmanı “süs” konumunda; gerçek AOI davranışı yok. |
| C3 | **Referans sayıları anlamsal olarak çelişkili.** `detected_count` ham YOLO komponent tespit sayısı (120), `expected_count` BOM uzunluğu (20); buna rağmen `issues: []` görünüyor. Eşleştirme one-to-many: aynı tespit birden fazla referans satırını tatmin edebiliyor. Fazla komponent (`extra_component`) kontrolü hiç yok. | `services/reference.py:104-172`, `schemas.py:52-58` | Kullanıcı “20 beklenen / 120 tespit / 0 sorun” görüp sisteme güvenini kaybediyor. Gerçek eksik/fazla komponent kaçırılabiliyor. |
| C4 | **Karar gerekçesi yok ve raporlar eksik.** Karar yalnızca string; hangi kusurun, hangi eşikle FAIL ürettiği görünmüyor. Ayrıca raporlar `inspect_image()` içinde, referans atanmadan önce üretiliyor → JSON/PDF hiçbir zaman `reference_check` içermiyor. Model bilgisi, analiz süresi, orijinal görüntü ve gerekçe de yok. | `services/decision.py`, `services/inspection.py:36`, `services/report.py` | Karar savunulamıyor; denetim/izlenebilirlik gereksinimi karşılanmıyor. |
| C5 | **Mock / gerçek model ayrımı API’de görünmüyor.** `USE_MOCK_DETECTOR=true` iken boş sonuç → PASS dönebiliyor; istemci bunu gerçek analiz sanıyor. | `services/detector.py:88-100`, `schemas.py:60-69` | Yanlış güven hissi; özellikle demo/ci ortamlarında tehlikeli. |

### Önemli

| # | Bulgu | Yer | Etki |
| --- | --- | --- | --- |
| I1 | **Görüntü doğrulama yetersiz.** EXIF yönü uygulanmıyor (`ImageOps.exif_transpose` yok), minimum piksel çözünürlüğü ve kanal/renk uzayı kontrolü yok. | `services/storage.py:31-40` | Telefon fotoğraflarında 90°/270° rotation gelirse YOLO kutuları ile görüntü uyumsuz olabilir. |
| I2 | **Eşzamanlılık güvenli değil.** Global `_detector` / `_detector` lazy init kilit kullanmıyor; iki istek aynı anda modeli iki kez yükleyebilir. CPU inference ~13 sn olduğu için threadpool tıkanması olası. | `services/detector.py:85-100`, `services/components.py:47-60` | Üretim yükünde bellek artışı ve tutarsız davranış. |
| I3 | **Hata yönetimi standart değil.** Model yüklenemezse / referans görüntüsü okunamazsa ham `ValueError` → 500. API hata cevabı için ortak şema yok. | `services/detector.py:34`, `services/reference.py:90-91`, `routers/*` | Hatalar kullanıcıya anlamlı gelmiyor, loglanmıyor. |
| I4 | **Kusur kapsamı belirsiz.** Model 9 sınıf destekliyor; `open_joint`, `rotation_error`, `unknown anomaly` için model/ağırlık yok. README ve istek listesi bunları “destekli” gibi gösteriyor. | `docs/MODELS.md`, `README.md:13-16` | Desteklenmeyen kusurların varlığı yanlışlıkla ima ediliyor. |
| I5 | **Hizalama başarısızlığı karara yansımıyor.** `aligned: false` durumunda normalize koordinat fallback’i sessizce kullanılıyor; karar MANUAL_REVIEW’a dönmüyor. | `services/reference.py:95`, `services/alignment.py:7-41` | Perspektif farkı büyükse yanlış eşleştirme → yanlış PASS/FAIL. |
| I6 | **Analiz geçmişi yok.** Sonuçlar sadece dosyaya yazılıyor; listeleme/arama/filtreleme API’si yok. Süre, model versiyonu, karar gerekçesi kaydedilmiyor. | `services/report.py`, `routers/` | Üretim istatistikleri ve “geçmiş analizi tekrar açma” mümkün değil. |
| I7 | **Test kapsamı dar.** Referansın karara etkisi, mock/real ayrımı, bozuk dosya, hizalama başarısızlığı, büyük görsel senaryoları test edilmiyor. Frontend’de lint/test yok. | `backend/tests/*` | Kritik C2/C3/C5 regresyonları yakalanmamış. |
| I8 | **Logging yok.** Analiz ID, model adı/versiyonu, süre, hata kaydı tutulmuyor. | tüm servisler | Operasyonel izlenebilirlik yok. |
| I9 | **Frontend monolitik.** Tüm UI tek `App.tsx` içinde; navigasyon, KPI, görüntüleyici (zoom/pan/filtre), empty/loading/error durumları yok. Responsive davranış zayıf. | `frontend/src/App.tsx`, `index.css` | Prototip hissi; endüstriyel yazılım standartlarına uymuyor. |

### Orta

| # | Bulgu | Yer |
| --- | --- | --- |
| M1 | YOLO `imgsz`/NMS/iou ayarları dışa açılmıyor; küçük kartlarda kaçırma riski, tiling/SAHI yok. | `services/detector.py:56-62` |
| M2 | `ReferenceComponent` yalnızca `x`,`y` taşıyor; genişlik/yükseklik/açı yok. Açı farkı hesaplanamıyor (bbox tabanlı açı tahmini uydurma olacağı için eklenmemeli). | `schemas.py:30-35` |
| M3 | Demo referansı `datasets/...` altındaki gitignored görsele işaret ediyor; temiz klonda referans geçersiz kalır. | `data/references/demo.json` |
| M4 | `torch` CPU-only kurulu, GPU mevcut; çıkarım ~13 sn. Bu eğitim değil, yalnızca hızlandırma konusu. | `.env`, ortam |

## Çalışan kısımlar (korunacak)

- Gerçek YOLO26 ağırlıkları indiriliyor, sınıf bazlı eşikler uygulanıyor ve gerçek çıkarım doğrulandı (4 `excess_solder`, en yüksek güven 0.826).
- Komponent modeli (`fine_best.pt`) çalışıyor; 120 tespit üretti.
- SIFT + RANSAC hizalama gerçek görselde `aligned: true` verdi.
- Dosya yükleme, benzersiz UUID adlandırma, boyut/format kontrolü temel düzeyde çalışıyor.
- JSON/PDF rapor dosyaları diske yazılıyor.
- Denetim anında 11 test geçiyordu; mevcut durumda 37 test ve production build başarılı.

## Desteklenmeyen / gerçek olmayan yetenekler (açıkça işaretli)

- `rotation_error`: **yok** (komponent modeli açı üretmiyor).
- `open_joint`: **yok** (model sınıfı yok; RGB fotoğrafta güvenilir değil).
- `unknown anomaly`: **yok** (anomaly detection modeli eklenmedi).
- Solder void: modelde var ama `insufficient_solder` ile karışıyor; düşük güvenilirlik.
- Gerçek üretim eşikleri: **doğrulanmadı**; mevcut eşikler model kartındaki F1-optimal değerler.

## Uygulama sırası (kullanıcı onaylı)

1. **Kritik düzeltmeler:** C1 medya proxy, C2/C3 referans + karar bütünleşmesi, C4 gerekçeli karar ve rapor, C5 mock/gerçek ayrımı.
2. **Sağlamlaştırma:** I1 EXIF/çözünürlük, I2 kilitli model yükleyici, I3 standart hata cevabı, I5 hizalama → MANUAL_REVIEW, I7/I8 test + loglama.
3. **Profesyonel arayüz:** sidebar, overview, görüntüleyici, geçmiş, raporlar, model performansı (gerçek metriklerle).
4. **AOI derinleştirme:** one-to-one eşleştirme iyileştirmeleri, tiling, gerçek metrik değerlendirmesi.
5. **Ürünleştirme:** geçmiş kaydı, kullanıcı ayarları, PostgreSQL (çok kullanıcılı aşamada).

Her aşama ayrı commit + push; mevcut testler her adımda çalıştırılacak.

## Düzeltme durumu

| Bulgu | Durum | Not |
| --- | --- | --- |
| C1 | ✅ Düzeltildi | Vite `/media` proxy eklendi; HTTP doğrulaması yapılacak. |
| C2 | ✅ Düzeltildi | `DecisionContext` referans sonucunu da değerlendiriyor; referans hataları FAIL üretiyor. |
| C3 | ✅ Düzeltildi | One-to-one eşleştirme, `extra_component`, güven eşiği ve ayrı sayıçlar eklendi. |
| C4 | ✅ Düzeltildi | `decision.reasons` yapılandırıldı; raporlar karar gerekçesi + referans + model + süre içeriyor. |
| C5 | ✅ Düzeltildi | `engine: real/mock` ve `MOCK_ENGINE` gerekçesi; mock asla PASS vermiyor. |
| I1 | ✅ Düzeltildi | EXIF yönü uygulanıyor, min çözünürlük kontrolü eklendi; gereksiz yeniden kodlama kaldırıldı. |
| I2 | ✅ Düzeltildi | Model yükleyicilerde çift kontrollü `threading.Lock`. |
| I3 | ✅ Düzeltildi | `{error, detail, request_id}` ortak gövdesi, `X-Request-ID`, HTTP/doğrulama/servis/beklenmeyen hata handler'ları. |
| I5 | ✅ Düzeltildi | Hizalama başarısızlığı → MANUAL_REVIEW. |
| I7 | ✅ Genişletildi | 37 test: karar, referans eşleştirme, yükleme doğrulama, hata şeması ve log korelasyonu. |
| I8 | ✅ Düzeltildi | Tek satırlık JSON log, `LOG_LEVEL`, istek/analiz olaylarında `request_id` korelasyonu. |
| I9 | ✅ Düzeltildi | Endüstriyel koyu tema, hash router, 7 sayfa, zoom/pan viewer, boş/yükleme/hata durumları, responsive. |

Doğrulanan demo sonucu (gerçek modellerle): 73 beklenen, 120 ham komponent tespiti, 73 eşik üstü, 73 eşleşen, 0 uyuşmazlık; karar FAIL ve gerekçesi yalnızca yüksek güvenli `excess_solder`.

## Düzeltme sonrası doğrulama (2026-11-19)

| Kontrol | Sonuç |
| --- | --- |
| `pytest backend/tests -q` | 37 passed, 2 warnings (Starlette/httpx deprecation) |
| `npm.cmd run build` | Başarılı (JS chunk >500 kB uyarısı, gzip ~193 kB) |
| `/media` proxy (Vite + API) | `200`, `image/jpeg`, 147.864 byte |
| Tarayıcıda 7 sayfa | Hatasız render, konsol hatası yok |
| Uçtan uca gerçek analiz | `FAIL` + `GERÇEK MODEL`, 4 `excess_solder`, referans 73/73, 640×640 işaretli görüntü |
| Geçmiş / raporlar / overview | 1 kayıt, JSON+PDF linkleri, gerçek KPI ve 2 grafik |
| Bozuk dosya `POST /api/v1/uploads` | `400`, `{"error":"bad_request","detail":...,"request_id":...}`, `X-Request-ID` başlığı |
| Eksik alan `POST /api/v1/uploads` | `422`, `error: validation_error` |
| JSON log olayları | `request_completed`, `api_error`, `validation_error`, `inspection_completed`; aynı `request_id` ile korele |
| `GET /api/v1/history/overview`, `/models`, `/settings` | `200`, her yanıtta `X-Request-ID` |

Not: bu doğrulamada `data/inspections.db` yerel demo kaydıyla doludur; dosya `.gitignore` kapsamındadır, temiz klonda geçmiş boş başlar. Referans BOM'u `data/references/demo.json` yine gitignored olduğu için temiz klonda yeniden oluşturulmalıdır.
