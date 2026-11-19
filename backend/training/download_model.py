from pathlib import Path

from huggingface_hub import hf_hub_download

MODEL_REPO = "ParsaVictor/pcb-solder-defect-detection-yolo26"
TARGET = Path("models/pcb-solder-defect-detection-yolo26")
FILES = ("best.pt", "thresholds.json")


def main() -> None:
    for filename in FILES:
        path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=filename,
            local_dir=TARGET,
        )
        print(f"İndirildi: {path}")


if __name__ == "__main__":
    main()
