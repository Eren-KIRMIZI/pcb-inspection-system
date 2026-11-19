from dataclasses import dataclass

from ..config import settings
from ..schemas import Decision, DecisionReason, Detection, EngineMode, ReferenceCheck

CRITICAL_DEFECT_CLASSES = {
    "solder_bridge",
    "missing_component",
    "shifted_component",
}
HIGH_SEVERITY_DEFECT_CLASSES = {
    "insufficient_solder",
    "excess_solder",
    "physical_damage",
    "burn",
}

REFERENCE_ISSUE_SEVERITY = {
    "missing_component": "critical",
    "wrong_component": "critical",
    "shifted_component": "high",
    "extra_component": "high",
}

REFERENCE_ISSUE_MESSAGE = {
    "missing_component": "Beklenen komponent bulunamadı",
    "wrong_component": "Beklenen konumda yanlış komponent tespit edildi",
    "shifted_component": "Komponent konum eşiğinin dışında",
    "extra_component": "Beklenmeyen fazla komponent tespit edildi",
}


@dataclass(frozen=True)
class DecisionContext:
    defects: list[Detection]
    reference_check: ReferenceCheck | None
    engine: EngineMode
    image_quality_ok: bool
    image_width: int
    image_height: int


def _reason(
    code: str,
    severity: str,
    source: str,
    message: str,
) -> DecisionReason:
    return DecisionReason(code=code, severity=severity, source=source, message=message)


def _defect_reasons(defects: list[Detection]) -> list[DecisionReason]:
    """Aynı sınıftaki tespitleri gruplayıp tek gerekçe üretir."""

    grouped: dict[str, list[Detection]] = {}
    for detection in defects:
        grouped.setdefault(detection.class_name, []).append(detection)

    reasons: list[DecisionReason] = []
    for class_name, items in sorted(grouped.items()):
        max_confidence = max(item.confidence for item in items)
        count = len(items)
        detail = f"{class_name}: {count} tespit, en yüksek güven %{max_confidence * 100:.1f}"

        if class_name.lower() in CRITICAL_DEFECT_CLASSES:
            reasons.append(
                _reason("CRITICAL_DEFECT", "critical", "defect", f"Kritik kusur — {detail}")
            )
        elif max_confidence >= settings.fail_min_confidence:
            reasons.append(
                _reason(
                    "HIGH_CONFIDENCE_DEFECT",
                    "high",
                    "defect",
                    f"Yüksek güvenli kusur (eşik %{settings.fail_min_confidence * 100:.0f}) — {detail}",
                )
            )
        else:
            reasons.append(
                _reason(
                    "UNCERTAIN_DEFECT",
                    "medium",
                    "defect",
                    f"Güven eşiğinin altında kusur, manuel inceleme gerekli — {detail}",
                )
            )
    return reasons


def _reference_reasons(check: ReferenceCheck) -> list[DecisionReason]:
    reasons: list[DecisionReason] = []

    if not check.aligned:
        reasons.append(
            _reason(
                "REFERENCE_ALIGNMENT_FAILED",
                "medium",
                "reference",
                "Referans ile test görseli hizalanamadı; koordinat karşılaştırması güvenilir değil.",
            )
        )

    for issue in check.issues:
        severity = REFERENCE_ISSUE_SEVERITY.get(issue.issue, "high")
        message = REFERENCE_ISSUE_MESSAGE.get(issue.issue, issue.issue)
        if issue.distance_px is not None:
            message += f" ({issue.ref}, {issue.distance_px} px)"
        elif issue.ref:
            message += f" ({issue.ref})"
        reasons.append(
            _reason(
                f"REFERENCE_{issue.issue.upper()}",
                severity,
                "reference",
                message,
            )
        )

    if check.expected_count > 0 and check.matched_count == 0:
        reasons.append(
            _reason(
                "REFERENCE_MATCH_FAILED",
                "high",
                "reference",
                "Beklenen komponentlerin hiçbiri eşleştirilemedi; referans kontrolü tamamlanmadı.",
            )
        )

    return reasons


def decide(context: DecisionContext) -> Decision:
    """Tespit, referans, görüntü kalitesi ve motor durumuna göre karar üretir."""

    reasons: list[DecisionReason] = []

    if context.engine == "mock":
        reasons.append(
            _reason(
                "MOCK_ENGINE",
                "medium",
                "engine",
                "Mock tespit motoru aktif; sonuç kalite kararı için kullanılamaz.",
            )
        )

    if not context.image_quality_ok:
        reasons.append(
            _reason(
                "LOW_RESOLUTION",
                "medium",
                "quality",
                f"Görüntü çözünürlüğü çok düşük ({context.image_width}x{context.image_height}); "
                f"en az {settings.min_image_width}x{settings.min_image_height} beklenir.",
            )
        )

    reasons.extend(_defect_reasons(context.defects))

    if context.reference_check is not None:
        reasons.extend(_reference_reasons(context.reference_check))
    else:
        reasons.append(
            _reason(
                "NO_REFERENCE_CHECK",
                "info",
                "reference",
                "Referans/BOM kontrolü yapılmadı; eksik komponent değerlendirilemedi.",
            )
        )

    if context.engine == "mock":
        verdict = "MANUAL_REVIEW"
    elif any(reason.severity in {"critical", "high"} for reason in reasons):
        verdict = "FAIL"
    elif any(reason.severity == "medium" for reason in reasons):
        verdict = "MANUAL_REVIEW"
    else:
        verdict = "PASS"
        reasons.append(
            _reason(
                "ALL_CHECKS_PASSED",
                "info",
                "engine",
                "Tespit edilen kusur yok; yapılan kontroller tamamlandı.",
            )
        )

    return Decision(verdict=verdict, reasons=reasons)
