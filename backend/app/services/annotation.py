from pathlib import Path
from uuid import uuid4

import cv2

from ..config import settings
from ..schemas import Detection


def draw_detections(image_path: Path, detections: list[Detection]) -> Path:
    """Tespitleri görüntü üzerine çizer ve işaretli kopyayı kaydeder."""

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Görüntü okunamadı: {image_path}")

    for detection in detections:
        x1, y1, x2, y2 = (int(value) for value in detection.bbox)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"{detection.class_name} {detection.confidence:.2f}"
        text_y = max(y1 - 8, 16)
        cv2.putText(
            image,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )

    settings.results_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.results_dir / f"annotated_{uuid4().hex}.jpg"
    if not cv2.imwrite(str(output_path), image):
        raise RuntimeError(f"İşaretli görüntü kaydedilemedi: {output_path}")
    return output_path
