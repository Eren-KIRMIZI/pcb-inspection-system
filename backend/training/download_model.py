from pathlib import Path

from huggingface_hub import hf_hub_download

MODELS = (
    (
        "ParsaVictor/pcb-solder-defect-detection-yolo26",
        Path("models/pcb-solder-defect-detection-yolo26"),
        ("best.pt", "thresholds.json"),
    ),
    (
        "ParsaVictor/pcb-component-detection-yolo26",
        Path("models/pcb-component-detection-yolo26"),
        ("fine_best.pt",),
    ),
)


def main() -> None:
    for repo_id, target, files in MODELS:
        for filename in files:
            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=target,
            )
            print(f"İndirildi: {path}")


if __name__ == "__main__":
    main()
