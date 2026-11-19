import argparse
from pathlib import Path

import yaml

DEFAULT_DATA = Path("datasets/pcb-solder-defect-detection/final_solder/data.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description="YOLO veri setinin bütünlüğünü kontrol eder.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(f"data.yaml bulunamadı: {args.data}")

    config = yaml.safe_load(args.data.read_text(encoding="utf-8"))
    root = args.data.parent
    class_count = int(config["nc"])
    names = config["names"]

    print(f"Sınıf sayısı: {class_count}")
    print(f"Sınıflar: {', '.join(names)}")

    for split in ("train", "val", "test"):
        image_dir = root / config[split]
        label_dir = root / "labels" / split
        images = sorted(image_dir.glob("*.*"))
        labels = sorted(label_dir.glob("*.txt"))
        print(f"{split}: {len(images)} görüntü, {len(labels)} etiket dosyası")

        bad_ids = 0
        for label_file in labels:
            for line in label_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                class_id = int(line.split()[0])
                if class_id < 0 or class_id >= class_count:
                    bad_ids += 1
        if bad_ids:
            print(f"  UYARI: {bad_ids} geçersiz sınıf ID'si bulundu")
        else:
            print("  Sınıf ID'leri geçerli")


if __name__ == "__main__":
    main()
