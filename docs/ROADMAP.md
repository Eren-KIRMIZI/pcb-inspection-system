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

## Aşama 1 tanımı (MVP)

- Kullanıcı bir PCB fotoğrafı yükler.
- Backend görüntüyü YOLO modeliyle analiz eder.
- Kusurlar görüntü üzerinde işaretlenir ve tabloya dökülür.
- Karar motoru PASS / FAIL / MANUAL REVIEW üretir.
- Sonuç JSON olarak döner ve arayüzde gösterilir.

Kamera, canlı görüntü ve donanım kalibrasyonu bu sürümde yoktur.
