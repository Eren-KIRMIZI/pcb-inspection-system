from pathlib import Path
from uuid import uuid4

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..config import BASE_DIR, settings
from ..schemas import InspectionResult


def _relative(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def _line(pdf: canvas.Canvas, text: str, x: float, y: float, size: int = 9) -> None:
    pdf.setFont("Helvetica", size)
    pdf.drawString(x, y, text[:120])


def _write_pdf(path: Path, result: InspectionResult) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    x = 50
    y = height - 50

    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(x, y, "PCB Inspection Report")
    y -= 26

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x, y, f"Karar: {result.verdict}")
    y -= 22

    meta = [
        f"Inspection ID: {result.image_id}",
        f"Dosya: {result.filename}",
        f"Tarih: {result.created_at.isoformat()}",
        f"Motor: {result.engine} | {result.model.defect_model}",
        f"Komponent modeli: {result.model.component_model or 'kullanilmadi'}",
        f"Aygit: {result.model.device} | Sure: {result.duration_ms} ms",
        f"Goruntu: {result.image_width}x{result.image_height}",
        f"Kusur sayisi: {len(result.defects)}",
    ]
    for line in meta:
        _line(pdf, line, x, y, 9)
        y -= 14

    y -= 8
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Karar Gerekceleri")
    y -= 18
    for reason in result.decision.reasons:
        if y < 60:
            pdf.showPage()
            y = height - 50
        _line(pdf, f"[{reason.severity}/{reason.source}] {reason.code}: {reason.message}", x, y, 8)
        y -= 13

    if result.reference_check is not None:
        check = result.reference_check
        if y < 90:
            pdf.showPage()
            y = height - 50
        y -= 8
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x, y, "Referans / BOM Kontrolu")
        y -= 18
        summary = [
            f"Referans: {check.reference} | Hizalama: {'basarili' if check.aligned else 'basarisiz'}",
            f"Beklenen: {check.expected_count} | Eslesen: {check.matched_count}",
            f"Ham tespit: {check.raw_component_detections} | Esik ustu: {check.qualified_component_detections}",
            f"Eksik: {check.missing_count} | Yanlis: {check.wrong_count} | Kaymis: {check.shifted_count} | Fazla: {check.extra_count}",
        ]
        for line in summary:
            _line(pdf, line, x, y, 9)
            y -= 14

        for issue in check.issues[:40]:
            if y < 60:
                pdf.showPage()
                y = height - 50
            _line(
                pdf,
                f"{issue.issue}: {issue.ref} / {issue.expected_type} -> {issue.detected_type or '-'}",
                x,
                y,
                8,
            )
            y -= 12

    if y < 90:
        pdf.showPage()
        y = height - 50
    y -= 8
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(x, y, "Tespit Edilen Kusurlar")
    y -= 18

    if not result.defects:
        _line(pdf, "Kusur tespit edilmedi.", x, y, 9)
    else:
        for defect in result.defects:
            if y < 60:
                pdf.showPage()
                y = height - 50
            bbox = ", ".join(f"{value:.0f}" for value in defect.bbox)
            _line(
                pdf,
                f"{defect.class_name} | conf={defect.confidence:.2f} | bbox={bbox}",
                x,
                y,
                8,
            )
            y -= 13

    pdf.save()


def generate_reports(result: InspectionResult) -> tuple[str, str]:
    """JSON ve PDF raporlarını oluşturup göreli yollarını döner."""

    settings.results_dir.mkdir(parents=True, exist_ok=True)
    base = settings.results_dir / f"report_{result.image_id}_{uuid4().hex[:6]}"

    json_path = base.with_suffix(".json")
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    pdf_path = base.with_name(f"{base.name}.pdf")
    _write_pdf(pdf_path, result)

    return _relative(json_path), _relative(pdf_path)
