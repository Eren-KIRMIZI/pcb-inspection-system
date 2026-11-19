# Teknik Borç ve AOI Engine 2.0 Ön Analizi

Tarih: 2026-11-19  
Kapsam: `main` @ `913ac90` yerel kopyası; backend/frontend kaynak kodu, testler, veri seti ve model dosyaları okundu. Çalışan sistem yeniden yazılmadı, yalnızca okuma yapıldı.  
Yöntem: kaynak kodu incelemesi + mevcut HTTP doğrulama sonuçları + veri seti/DB sayımları.

## 1. Mevcut yapı (korunacak)

| Katman | Dosyalar | rol |
| --- | --- | --- |
| Çıkarım | `services/detector.py`, `services/components.py` | Kusur ve komponent YOLO modelleri, kilitli lazy-load |
| Hizalama | `services/alignment.py` | SIFT + BFMatcher + RANSAC homografi |
| Referans | `services/reference.py` | BOM eşleştirme, eksik/yanlış/kaymış/fazla |
| Karar | `services/decision.py` | Gerekçeli PASS / FAIL / MANUAL_REVIEW |
| Akış | `services/inspection.py` | Yükleme → tespit → referans → karar → rapor → geçmiş |
| Rapor | `services/report.py`, `services/annotation.py` | JSON/PDF ve işaretli görüntü |
| Geçmiş | `services/history.py` | SQLite, overview/istatistik |
| Arayüz | `frontend/src/pages/*`, `components/*` | 7 sayfa, hash router, Industrial Dark tema |
| Altyapı | `errors.py`, `logging_config.py`, `middleware.py` | Ortak hata şeması, JSON log, request ID |

Doğrulananlar: 37 test geçiyor, production build başarılı, gerçek modaller aktif (`USE_MOCK_DETECTOR=false`, `DEVICE=cpu`), işaretli görüntü hem Vite hem API üzerinden `200 image/jpeg`.

## 2. Veri durumu

- `datasets/pcb-solder-defect-detection/final_solder`: train 3.836 görüntü / 12.704 kutu, val 687 / 734, test 686 / 663. Etiketler YOLO formatında; uygulama içi değerlendirme için gerçek ground truth mevcut.
- `models/pcb-solder-defect-detection-yolo26/thresholds.json`: global 0.228 + 9 sınıf eşiği (F1-optimal).
- `data/inspections.db`: 2 kayıt, ikisi de aynı dataset görselinin gerçek analizi. **Sentetik/demo kayıt yok.** Grafiklerin boş görünmesi veri azlığından, uydurma veri eklenmesinden değil.
- `data/references/demo.json` ve `data/` gitignored; temiz klonda referans yeniden oluşturulmalı.

## 3. Teknik borçlar

Öncelik: P0 = yanlış sonuç/güven riski, P1 = yeni aşamanın ön koşulu, P2 = deneyim, P3 = bakım.

| # | Öncelik | Bulgu | Yer | Etki / öneri |
| --- | --- | --- | --- | --- |
| D1 | P0 | `overview(days)` KPI, kusur dağılımı ve son analizleri **tüm geçmişten** hesaplıyor; sadece `trend` tarih aralığına göre filtreleniyor. | `services/history.py:193-267`, `routers/history.py:14-16` | Tarih filtresi bugün yalnızca grafiği değiştiriyor. Tüm sorgulara tarih `WHERE` eklenmeli; önceki dönem toplamları ayrı sorguyla alınmalı. |
| D2 | P0 | Hizalama yalnızca `matrix \| None` döner; inlier oranı, ölçek, açı veya güven bilgisi yok. Her analizde SIFT yeniden hesaplanıyor. | `services/alignment.py:7-41`, `services/reference.py:100` | Hizalamanın "başarılı" olması tek başına güven göstergesi değil. `AlignmentResult(matrix, inlier_count, inlier_ratio, scale, rotation_deg)` döndürülmeli; eşik altı `MANUAL_REVIEW`; referans görüntü hash'iyle önbellek. |
| D3 | P0 | Eşleştirme BOM sırasına göre açgözlü en yakın komşu; iki referans aynı tespit için yarışırsa global optimum kaçılıyor. Tip eşleşmesi yalnızca merkez mesafesi + isim; bbox alanı/çakışma kontrolü yok. | `services/reference.py:120-192` | Global atama (Hungarian/min-cost) + mesafe/tip/alan/güven maliyeti gerekli. `extra_component` kaydında `ref="—"` decision mesajına `(—)` olarak yansıyor; anlamlı ID üretilmeli. |
| D4 | P0 | Komponent modeli açı üretmiyor; referans şeması yalnızca `x,y` taşıyor. YOLO bbox'ından açı türetmek uydurma olur. | `schemas.py:42-46`, `system.py:51-54` | "Konum ve rotasyon analizi" (commit 19) için ya ground truth/template tabanlı yöntem eklenmeli ya da kapsam dışı bırakılmalı. Karar verilmeden uygulanmamalı. |
| D5 | P1 | Kusur çıkarımında `imgsz`, IoU/NMS ve tiling parametreleri dışa açılmamış; tile birleştirme (stitch + dedup) yok. | `services/detector.py:74-80` | Tiling (commit 20) için `imgsz` ayarı, overlap, kutu koordinat map'i ve tile'lar arası NMS gerekiyor; sınıf eşikleri korunmalı. |
| D6 | P1 | Uygulama içi metrik yok; `/models` yalnızca model kartı değerlerini gösteriyor ve `unmeasured_metrics` listesini açıkça veriyor. | `routers/system.py:19-84` | Test split'i (686 görüntü/663 kutu) ile offline CLI değerlendirme: precision, recall, F1, AP50/AP50-95, FN/FP, sınıf bazında ve inference süresi. Sonuç `data/evaluation/*.json` (gitignored); ölçüm yoksa `/models` `measured_in_app=false` kalmalı. |
| D7 | P1 | `manual_review_min_confidence` tanımlı ama hiçbir yerde kullanılmıyor. | `config.py:32` | Karar motoruna bağlanmalı ya da kaldırılmalı; ölü ayar yanıltıcı. |
| D8 | P1 | Komponent modeli eksikse düz `RuntimeError` → 500; kusur modeli `ModelUnavailableError` → 503. | `components.py:17`, `detector.py:46` | Aynı hata sınıfı kullanılmalı. |
| D9 | P2 | İngilizce sınıf adları arayüzde ham görünüyor; işaretli görüntü ve PDF de İngilizce yazıyor. | `Overview.tsx:128`, `PcbViewer.tsx:174`, `ResultPanel.tsx:50`, `annotation.py:20`, `report.py:109` | Frontend etiket haritası güvenli (`excess_solder → Fazla Lehim`), backend sınıf adları korunur. Görüntü/PDF metnini değiştirmek ayrı karar. |
| D10 | P2 | Overview "Motor Durumu" `/settings` çıktısından türetiliyor; model dosyası/disk erişimi gerçekten sorgulanmıyor. | `Overview.tsx:174-184`, `routers/system.py:87-109` | `/status` endpoint'i: model dosyası var mı/yüklendi mi, komponent modeli, `data_dir` yazılabilir mi, DB erişilebilir mi; ayrı ayrı alanlar. |
| D11 | P2 | Tarih aralığı yalnızca 1–90 gün; özel aralık yok. | `routers/history.py:15` | `date_from`/`date_to` sorgu parametreleri eklenmeli (D1 ile birlikte). |
| D12 | P2 | Görüntü kalitesi yalnızca min çözünürlük; bulanıklık/poşlama kontrolü yok. | `inspection.py:59-62` | Eklenecekse eşikler gerçek görüntülerle kalibre edilmeli; keyfi eşik PASS/FAIL'i bozar. |
| D13 | P3 | Frontend `getOverview(7)` sabit; filtre UI'ı yok. | `api.ts:39-41`, `Overview.tsx:51` | D1/D11 tamamlandıktan sonra 7/30/90/özel seçici bağlanmalı. |
| D14 | P3 | ROADMAP'te 16. adım "gerçek model değerlendirme" olarak duruyor; yeni planda 16 = hizalama. | `docs/ROADMAP.md` | Plan onaylandıktan sonra numaralar güncellenmeli. |

## 4. Önerilen uygulama sırası (debt-first, mevcut kodu koruyarak)

1. **16 — Hizalama:** D2. `AlignmentResult` + güven eşiği + önbellek; mevcut `compare_board` imzası korunur.
2. **17 — Eşleştirme motoru:** D3. Global atama; `ReferenceCheck` alanları korunur, yeni alanlar eklenir.
3. **18 — Fark analizi:** D3/D8 çıktıları; gerekçe kodları genişletilir, `extra_component` kimliği düzeltilir.
4. **19 — Poz/rotasyon:** D4 kararı alınmadan başlanmaz.
5. **20 — Tiling:** D5 + `imgsz`/IoU ayarları; sınıf eşikleri ve rapor şeması korunur.
6. **21/22 — Değerlendirme:** D6, sınıf bazlı metrikler dahil; ölçüm yoksa "ölçülmedi" denir.
7. **23 — Regresyon testleri:** her adımda test + `npm.cmd run build`.
8. **Dashboard paketi (bağımsız):** D1 + D11 + D13 (doğru dönem istatistikleri), D10 (gerçek sistem durumu), D9 (Türkçe etiketler). Bu paket motoru engellemez; D1 yanlış KPI ürettiği için erken yapılması önerilir.

Her adım ayrı commit + push; testler her adımda çalıştırılır. Demo/sentetik veri eklenmez; mevcut 2 kayıt gerçek analizdir ve korunur.

## 5. Karar gerektiren noktalar

- **Rotasyon:** kapsam dışı bırakılmalı mı, yoksa referans şablonu + güven skoruyla mı ölçülmeli? (bbox'tan açı uydurmak seçenek değil)
- **Dashboard:** D1/D10/D9 düzeltmeleri motor çalışmasından önce mi, sonra mı?
- **Yerel DB:** 2 gerçek kayıt korunacak mı, yoksa temiz bir başlangıç için silinecek mi? (silme işlemi kullanıcı onayı gerektirir)
