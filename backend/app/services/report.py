import json
from pathlib import Path
from uuid import uuid4

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..config import BASE_DIR, settings
from ..schemas import InspectionResult


def _relative(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def _write_pdf(path: Path, result: InspectionResult) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "PCB Inspection Report")
    y -= 28

    pdf.setFont("Helvetica", 10)
    for line in (
        f"Image ID: {result.image_id}",
        f"Verdict: {result.verdict}",
        f"Created: {result.created_at.isoformat()}",
        f"Defect count: {len(result.defects)}",
    ):
        pdf.drawString(50, y, line)
        y -= 16

    y -= 12
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Defects")
    y -= 20
    pdf.setFont("Helvetica", 9)

    if not result.defects:
        pdf.drawString(50, y, "No defects detected.")
    else:
        for defect in result.defects:
            if y < 60:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 9)
            bbox = ", ".join(f"{value:.0f}" for value in defect.bbox)
            pdf.drawString(
                50,
                y,
                f"{defect.class_name} | conf={defect.confidence:.2f} | bbox={bbox}"[:110],
            )
            y -= 14

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
