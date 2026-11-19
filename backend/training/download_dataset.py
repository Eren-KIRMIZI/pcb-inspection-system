import argparse
import zipfile
from pathlib import Path

from huggingface_hub import snapshot_download

DATASET_ID = "ParsaVictor/pcb-solder-defect-detection"
DEFAULT_TARGET = Path("datasets/pcb-solder-defect-detection")
ZIP_NAME = "images_and_labels.zip"
INNER_ROOT = "final_solder"


def _extract(zip_path: Path, target: Path) -> Path:
    extracted = target / INNER_ROOT
    if (extracted / "images" / "train").exists():
        return extracted
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target)
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser(description="PCB lehim/komponent veri setini indirir.")
    parser.add_argument("--repo-id", default=DATASET_ID)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    downloaded = Path(
        snapshot_download(
            repo_id=args.repo_id,
            repo_type="dataset",
            local_dir=args.target,
        )
    )
    zip_path = downloaded / ZIP_NAME
    if zip_path.exists():
        data_root = _extract(zip_path, downloaded)
        print(f"Veri seti hazır: {data_root}")
    else:
        print(f"Veri seti indirildi: {downloaded}")


if __name__ == "__main__":
    main()
