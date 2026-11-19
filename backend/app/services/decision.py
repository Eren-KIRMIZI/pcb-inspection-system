from ..config import settings
from ..schemas import Detection

CRITICAL_CLASSES = {
    "missing_component",
    "shifted_component",
    "solder_bridge",
}


def decide(detections: list[Detection]) -> str:
    """Tespitlere göre kalite kararını üretir.

    - Kritik sınıflardan biri görülürse doğrudan FAIL.
    - Yüksek güvenli diğer kusurlar FAIL.
    - Orta güvenli kusurlar MANUAL_REVIEW.
    - Düşük güvenli gürültüler PASS.
    """

    if not detections:
        return "PASS"

    if any(item.class_name in CRITICAL_CLASSES for item in detections):
        return "FAIL"

    max_confidence = max(item.confidence for item in detections)
    if max_confidence >= settings.fail_min_confidence:
        return "FAIL"
    if max_confidence >= settings.manual_review_min_confidence:
        return "MANUAL_REVIEW"
    return "PASS"
