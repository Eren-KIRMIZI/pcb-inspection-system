# Hazır Modeller

Lokal eğitim gerekmez. Proje, eğitilmiş YOLO26 ağırlıklarını Hugging Face’den indirir.

## Lehim / montaj kusurları (aktif model)

| Model | Repo | Test mAP50 | Test mAP50-95 |
| --- | --- | --- | --- |
| YOLO26m | [`ParsaVictor/pcb-solder-defect-detection-yolo26`](https://huggingface.co/ParsaVictor/pcb-solder-defect-detection-yolo26) | 0.895 | 0.657 |

İndirme:

```powershell
.\.venv\Scripts\python.exe -m backend.training.download_model
```

İnen dosyalar:

- `models/pcb-solder-defect-detection-yolo26/best.pt` (~44 MB)
- `models/pcb-solder-defect-detection-yolo26/thresholds.json` (sınıf bazlı eşikler)

`.env` dosyası kök dizinde oluşturulur (`.env.example` örnek alınabilir):

```env
MODEL_PATH=models/pcb-solder-defect-detection-yolo26/best.pt
THRESHOLDS_PATH=models/pcb-solder-defect-detection-yolo26/thresholds.json
USE_MOCK_DETECTOR=false
DEVICE=0
CONF_THRESHOLD=0.228
```

GPU yoksa `DEVICE=cpu` kullanın.

## Sınıf bazlı eşikler

Model kartındaki F1-optimal değerler `thresholds.json` içinden okunur:

| Sınıf | Eşik |
| --- | --- |
| insufficient_solder | 0.297 |
| excess_solder | 0.349 |
| solder_bridge | 0.417 |
| solder_void | 0.249 |
| missing_component | 0.381 |
| shifted_component | 0.389 |
| burn | 0.224 |
| physical_damage | 0.214 |
| oxidation | 0.228 |

Bilinen zayıflıklar: `solder_void` sıklıkla `insufficient_solder` ile karışır; `burn` recall’i düşüktür (~62%); koyu fotoğraflarda performans düşer.

## Diğer hazır modeller (gelecek aşamalar)

| Model | Repo | Kullanım |
| --- | --- | --- |
| Bare-board YOLO26s | [`pcb-bare-board-defect-detection-yolo26`](https://huggingface.co/ParsaVictor/pcb-bare-board-defect-detection-yolo26) | Çıplak kart iz/kopper kusurları (şu an kapalı) |
| Component locator YOLO26s | [`pcb-component-detection-yolo26`](https://huggingface.co/ParsaVictor/pcb-component-detection-yolo26) | `any_best.pt` / `fine_best.pt`: komponent konumu ve türü |

Lisans: research/development. Ticari kullanım için model sahibiyle iletişime geçin.
