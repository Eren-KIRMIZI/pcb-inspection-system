# Model Eğitimi (opsiyonel)

Proje varsayılan olarak hazır eğitilmiş modeli kullanır; lokal eğitim **gerekli değildir**. Bkz. [`MODELS.md`](MODELS.md).  
Aşağıdaki adımlar yalnızca kendi modelini eğitmek istersen geçerlidir.

## 1. Veri setini indir

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-train.txt
.\.venv\Scripts\python.exe -m backend.training.download_dataset
```

Varsayılan hedef: `datasets/pcb-solder-defect-detection/final_solder/` (repo dışında, `.gitignore` ile hariç). Betik zip dosyasını otomatik açar.

Kullanılan veri seti: [`ParsaVictor/pcb-solder-defect-detection`](https://huggingface.co/datasets/ParsaVictor/pcb-solder-defect-detection)

- 5.209 görüntü: 3.836 train / 687 val / 686 test
- 9 sınıf: `insufficient_solder`, `excess_solder`, `solder_bridge`, `solder_void`, `missing_component`, `shifted_component`, `burn`, `physical_damage`, `oxidation`
- YOLO formatı, ~401 MB

Dikkat: `oxidation` sınıfı val/test split’lerinde 0 kutu içeriyor; bu sınıfın metriği güvenilmez olabilir.

## 2. Veri setini doğrula (opsiyonel)

```powershell
.\.venv\Scripts\python.exe -m backend.training.verify_dataset
```

Beklenen çıktı: train 3.836, val 687, test 686 görüntü; hepsinde eşleşen etiket dosyası ve geçerli sınıf ID'leri.

## 3. Eğitimi başlat

```powershell
.\.venv\Scripts\python.exe -m backend.training.train_yolo --device 0 --epochs 150 --imgsz 800
```

GPU yoksa `--device cpu` kullanılabilir, ancak eğitim çok daha uzun sürer.

## 4. Modeli uygulamaya bağla

Eğitim çıktısı `runs/pcb/solder_yolo/weights/best.pt` olur. Bu dosyayı `models/` altına kopyalayıp kök dizindeki `.env` dosyasını güncelle:

```env
MODEL_PATH=models/best.pt
USE_MOCK_DETECTOR=false
DEVICE=cpu
CONF_THRESHOLD=0.25
```

Ardından API’yi yeniden başlat. Mock detector yerine gerçek YOLO modeli kullanılır.

## Notlar

- Sınıf dengesizliği var: `solder_bridge` 4.522 örnek, `shifted_component` 512 örnek. Gerekirse sınıf ağırlıkları veya örnekleme denenebilir.
- Referans/BOM karşılaştırması bu eğitimden bağımsız, ayrı bir katmandır.
