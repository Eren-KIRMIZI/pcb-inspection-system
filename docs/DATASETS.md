# Veri Seti Araştırması

Son doğrulama: 2026-11-19. Kaynaklar güncel Hugging Face / GitHub / CVF sayfalarından kontrol edildi.

## Uygunluk tablosu

| Veri seti | İçerik | Boyut / erişim | Karar |
| --- | --- | --- | --- |
| [`ParsaVictor/pcb-solder-defect-detection`](https://huggingface.co/datasets/ParsaVictor/pcb-solder-defect-detection) | Montaj sonrası 9 sınıf: `insufficient_solder`, `excess_solder`, `solder_bridge`, `solder_void`, `missing_component`, `shifted_component`, `burn`, `physical_damage`, `oxidation` | 5.209 görüntü (3.836 / 687 / 686), YOLO formatı, ~401 MB, araştırma/geliştirme lisansı | **MVP birincil veri seti** |
| [`ParsaVictor/pcb-component-detection`](https://huggingface.co/datasets/ParsaVictor/pcb-component-detection) | 13 komponent sınıfı: resistor, capacitor, IC, electrolytic capacitor, transistor, diode, inductor, connector, marker, other, LED, switch/button, oscillator | 3.618 görüntü (3.005 / 321 / 292), 1024px kırpıntı, ~860 MB, araştırma/geliştirme lisansı | **İkincil:** komponent lokalizasyonu ve gelecekteki BOM eşleştirme |
| [`ParsaVictor/pcb-bare-board-defect-detection`](https://huggingface.co/datasets/ParsaVictor/pcb-bare-board-defect-detection) | Çıplak kart kusurları: `open_circuit`, `mouse_bite`, `spur`, `spurious_copper`, `short`, `missing_hole`, `pin_hole` | 21.656 görüntü, ~8.04 GB, karma kaynak (PKU-Market-PCB + DeepPCB + yeni çekimler) | **Şimdilik dışlandı:** montaj sonrası fotoğraf senaryosuna uygun değil ve çok büyük |
| [`DeepPCB`](https://github.com/tangsanli5201/DeepPCB) | 1.500 hizalı template/test çifti, 640×640; `open`, `short`, `mousebite`, `spur`, `spurious copper`, `pin-hole` | MIT görünümlü repo notu: yalnızca araştırma amaçlı | **Referans/benchmark.** Çıplak kart olduğu için MVP dışı; bare-board setine dahil |
| [`PCB-SAID` (ICCV 2025 Workshop)](https://openaccess.thecvf.com/content/ICCV2025W/VISION%2725/html/Mineo_PCB-SAID_A_Low-Cost_Camera-Based_Dataset_for_Few-Shot_SMD_Assembly_Inspection_ICCVW_2025_paper.html) | 175 RGB görüntü, 66 ince sınıf; iyi lehimli, kaymış/kalkmış/döndürülmüş, eksik ve kısa devre; bbox + poligon maske | "Available upon request" — doğrudan indirme yok | **Takipte:** erişim izne tabii ve küçük; few-shot referans olarak değerlendirilecek |
| Diğer adaylar (ön inceleme) | `tutitata/PCB_COMPONENTS_LABELLED` (5/17 sınıf), `Arshia82sbn/pcb-object-detection-dataset` (21 sınıf), `nvidia/Cosmos-AnomalyGen-PCB-Dataset` (86 örnek, segmentasyon) | Hugging Face | İhtiyaç olursa incelenecek; MVP için gerekli değil |

## Önemli notlar

- `pcb-solder-defect-detection` içinde `oxidation` sınıfı val/test split'lerinde **0 kutu** içeriyor; bu sınıfın metriği güvenilmez olabilir.
- Aynı veri setinde `shifted_component` ve `missing_component` örnekleri bulunması, MVP'nin temel gereksinimlerini doğrudan karşılıyor.
- Bare-board veri setleri (DeepPCB / PKU-Market-PCB türevleri) lehim veya eksik komponent tespiti için uygun değildir; karışıklığa yol açmamak için MVP'ye alınmadı.

## MVP veri stratejisi

1. `pcb-solder-defect-detection` ile tek aşamalı YOLO çıkarımı: eksik + kaymış komponent ve lehim kusurları.
2. `pcb-component-detection` ile komponent varlığı/konumu; BOM veya referans koordinatları gelirse karşılaştırma katmanı.
3. Çıplak kart verisi ve izne tabii PCB-SAID Aşama 2'ye bırakılır.

## İndirme örneği

```python
from huggingface_hub import snapshot_download

path = snapshot_download(
    repo_id="ParsaVictor/pcb-solder-defect-detection",
    repo_type="dataset",
)
```

Veri dosyaları `.gitignore` ile repo dışında tutulur; yalnızca indirme/kurulum betikleri commit edilir.
