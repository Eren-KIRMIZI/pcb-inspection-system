from backend.app.schemas import Detection
from backend.app.services.decision import decide


def _detection(name: str, confidence: float) -> Detection:
    return Detection(
        class_id=0,
        class_name=name,
        confidence=confidence,
        bbox=[0.0, 0.0, 10.0, 10.0],
    )


def test_no_detections_pass() -> None:
    assert decide([]) == "PASS"


def test_critical_class_fails_even_at_low_confidence() -> None:
    assert decide([_detection("missing_component", 0.30)]) == "FAIL"


def test_high_confidence_noncritical_fails() -> None:
    assert decide([_detection("insufficient_solder", 0.80)]) == "FAIL"


def test_medium_confidence_needs_review() -> None:
    assert decide([_detection("burn", 0.50)]) == "MANUAL_REVIEW"


def test_low_confidence_noise_passes() -> None:
    assert decide([_detection("burn", 0.20)]) == "PASS"
