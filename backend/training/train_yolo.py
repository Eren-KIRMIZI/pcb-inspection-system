import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="PCB kusur tespiti için YOLO eğitimi.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("datasets/pcb-solder-defect-detection/final_solder/data.yaml"),
    )
    parser.add_argument("--weights", default="yolo26m.pt")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--imgsz", type=int, default=800)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--project", default="runs/pcb")
    parser.add_argument("--name", default="solder_yolo")
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(
            f"data.yaml bulunamadı: {args.data}\n"
            "Önce: python -m backend.training.download_dataset"
        )

    from ultralytics import YOLO

    model = YOLO(args.weights)
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
        project=args.project,
        name=args.name,
    )


if __name__ == "__main__":
    main()
