from backend.app.schemas import (
    Detection,
    ReferenceCheck,
    ReferenceIssue,
)
from backend.app.services.decision import DecisionContext, decide


def _detection(name: str, confidence: float) -> Detection:
    return Detection(
        class_id=0,
        class_name=name,
        confidence=confidence,
        bbox=[0.0, 0.0, 10.0, 10.0],
    )


def _context(
    defects: list[Detection] | None = None,
    reference: ReferenceCheck | None = None,
    engine: str = "real",
    quality_ok: bool = True,
) -> DecisionContext:
    return DecisionContext(
        defects=defects or [],
        reference_check=reference,
        engine=engine,
        image_quality_ok=quality_ok,
        image_width=800,
        image_height=600,
    )


def _reference(issues: list[ReferenceIssue], aligned: bool = True) -> ReferenceCheck:
    return ReferenceCheck(
        reference="demo",
        aligned=aligned,
        expected_count=1,
        raw_component_detections=1,
        qualified_component_detections=1,
        matched_count=1 if not issues else 0,
        missing_count=sum(1 for issue in issues if issue.issue == "missing_component"),
        wrong_count=sum(1 for issue in issues if issue.issue == "wrong_component"),
        shifted_count=sum(1 for issue in issues if issue.issue == "shifted_component"),
        extra_count=sum(1 for issue in issues if issue.issue == "extra_component"),
        issues=issues,
    )


def test_no_defects_real_engine_passes() -> None:
    decision = decide(_context())
    assert decision.verdict == "PASS"
    assert any(reason.code == "ALL_CHECKS_PASSED" for reason in decision.reasons)


def test_critical_class_fails() -> None:
    decision = decide(_context([_detection("solder_bridge", 0.30)]))
    assert decision.verdict == "FAIL"
    assert any(reason.code == "CRITICAL_DEFECT" for reason in decision.reasons)


def test_high_confidence_fails() -> None:
    decision = decide(_context([_detection("insufficient_solder", 0.80)]))
    assert decision.verdict == "FAIL"
    assert any(reason.code == "HIGH_CONFIDENCE_DEFECT" for reason in decision.reasons)


def test_medium_confidence_needs_review() -> None:
    decision = decide(_context([_detection("burn", 0.50)]))
    assert decision.verdict == "MANUAL_REVIEW"
    assert any(reason.code == "UNCERTAIN_DEFECT" for reason in decision.reasons)


def test_mock_engine_never_returns_pass() -> None:
    decision = decide(_context(engine="mock"))
    assert decision.verdict == "MANUAL_REVIEW"
    assert any(reason.code == "MOCK_ENGINE" for reason in decision.reasons)


def test_low_resolution_needs_review() -> None:
    decision = decide(_context(quality_ok=False))
    assert decision.verdict == "MANUAL_REVIEW"
    assert any(reason.code == "LOW_RESOLUTION" for reason in decision.reasons)


def test_alignment_failure_needs_review() -> None:
    decision = decide(_context(reference=_reference([], aligned=False)))
    assert decision.verdict == "MANUAL_REVIEW"
    assert any(
        reason.code == "REFERENCE_ALIGNMENT_FAILED" for reason in decision.reasons
    )


def test_missing_component_fails() -> None:
    issue = ReferenceIssue(ref="C4", expected_type="capacitor", issue="missing_component")
    decision = decide(_context(reference=_reference([issue])))
    assert decision.verdict == "FAIL"
    assert any(
        reason.code == "REFERENCE_MISSING_COMPONENT" for reason in decision.reasons
    )


def test_extra_component_fails() -> None:
    issue = ReferenceIssue(ref="—", expected_type="—", issue="extra_component")
    decision = decide(_context(reference=_reference([issue], aligned=False)))
    assert decision.verdict == "FAIL"


def test_reasons_include_source_and_severity() -> None:
    decision = decide(_context([_detection("excess_solder", 0.9)]))
    assert all(reason.source in {"defect", "reference", "quality", "engine"} for reason in decision.reasons)
    assert all(reason.severity in {"critical", "high", "medium", "low", "info"} for reason in decision.reasons)
