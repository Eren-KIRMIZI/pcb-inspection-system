# Referans / BOM Karşılaştırması

Amaç: Kartta **bulunması gereken** komponentleri bilerek eksik, yanlış türde ve kaymış parçaları tespit etmek. YOLO tek başına bir parçanın olmamasını göremediği için beklenen liste gereklidir.

## BOM formatı

`components` listesi; `ref` devre üzerindeki referans, `type` komponent sınıfı, `x`/`y` referans görsel üzerinde **normalize** koordinat (0–1).

```json
{
  "components": [
    { "ref": "R15", "type": "resistor", "x": 0.124, "y": 0.317 },
    { "ref": "C08", "type": "capacitor", "x": 0.281, "y": 0.452 },
    { "ref": "U02", "type": "ic", "x": 0.512, "y": 0.604 }
  ]
}
```

Desteklenen türler (büyük/küçük harf duyarsız): `resistor`, `capacitor`, `electrolytic capacitor`, `ic`, `transistor`, `diode`, `inductor`, `connector`, `marker`, `led`, `switch/button`, `oscillator`. Kısa alias’lar da çalışır: `r`, `c`, `u`, `d`, `l`, `j`, `q`, `y`, `sw`.

## Referans kaydetme

`POST /api/v1/references` (multipart):

- `name`: referans adı (ör. `demo`). Sadece harf, rakam, `-` ve `_`.
- `image`: sağlam kart fotoğrafı.
- `bom`: yukarıdaki JSON dosyası.

Referans JSON’u `data/references/<name>.json` altına kaydedilir (repo dışında).

## Analizde kullanma

`POST /api/v1/inspections` isteğine `reference_name` alanı eklenir:

```python
files = {"file": ("board.jpg", image_bytes, "image/jpeg")}
data = {"reference_name": "demo"}
response = requests.post("http://localhost:8000/api/v1/inspections", files=files, data=data)
```

Sonuçta `reference_check` alanı döner:

```json
{
  "reference": "demo",
  "aligned": true,
  "expected_count": 20,
  "detected_count": 120,
  "issues": []
}
```

## Sorun türleri

| Sorun | Anlamı |
| --- | --- |
| `missing_component` | Beklenen konumda aynı türden komponent yok |
| `wrong_component` | Konumda komponent var ama türü farklı |
| `shifted_component` | Tür doğru ama merkez kayması eşikten büyük |

Mesafeler görüntü genişliğine göre ölçeklenir (`reference_match_distance_ratio=0.02`, `reference_shift_distance_ratio=0.015`).

## Hizalama

Referans ve test görseli arasında SIFT + RANSAC homografisi hesaplanır. Yeterli özellik eşleşmesi yoksa `aligned: false` döner ve normalize koordinatlar doğrudan kullanılır. Aynı kamera/kadro koşullarında hizalama başarılı olur; büyük açı/ölçek farklarında referans yeniden çekilmelidir.

## Sınırlar

- Komponent sınıflandırma modeli (`fine_best.pt`) test mAP50 ~0.432; küçük 0402 parçalar ve benzer görünen türler zayıf olabilir.
- Model 1024px kırpıntılarla eğitildi; tam kart görselinde küçük parçalar kaçırılabilir. İleride tiling eklenebilir.
- Bu katman lehim kusuru modelinden bağımsızdır; ikisi aynı analizde birlikte çalışır.
