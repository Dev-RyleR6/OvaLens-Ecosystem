import io
import csv
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.batch import BatchModel
from app.models.session import CandlingSessionModel
from app.models.scan import EggScanModel
from app.core.exceptions import EntityNotFoundException

try:
    # pyrefly: ignore [missing-import]
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    _HAVE_REPORTLAB = True
except ImportError:
    _HAVE_REPORTLAB = False


class ReportService:
    @staticmethod
    def generate_batch_csv(db: Session, batch_id: str) -> str:
        batch = db.query(BatchModel).filter(BatchModel.batch_id == batch_id).first()
        if not batch:
            raise EntityNotFoundException(f"Batch '{batch_id}' not found.")

        scans = db.query(EggScanModel).filter(EggScanModel.batch_id == batch_id).order_by(EggScanModel.scanned_at).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Scan ID", "Batch ID", "Session ID", "Sequence Number",
            "Final Class", "Confidence", "Latency (ms)", "Routing Action",
            "Scanned At", "Synced At"
        ])

        for scan in scans:
            writer.writerow([
                str(scan.scan_id),
                scan.batch_id,
                str(scan.session_id),
                scan.sequence_number,
                scan.final_class.value,
                float(scan.confidence),
                scan.inference_ms,
                scan.routing_action.value,
                scan.scanned_at.isoformat(),
                scan.synced_at.isoformat()
            ])

        return output.getvalue()

    @staticmethod
    def generate_batch_pdf(db: Session, batch_id: str) -> bytes:
        batch = db.query(BatchModel).filter(BatchModel.batch_id == batch_id).first()
        if not batch:
            raise EntityNotFoundException(f"Batch '{batch_id}' not found.")

        sessions = db.query(CandlingSessionModel).filter(CandlingSessionModel.batch_id == batch_id).order_by(CandlingSessionModel.stage).all()

        if _HAVE_REPORTLAB:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Title"],
                fontSize=18,
                leading=22,
                textColor=colors.HexColor("#800000"),
                alignment=0
            )
            sub_style = ParagraphStyle(
                "DocSub",
                parent=styles["Normal"],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#5C0000")
            )

            elements = []
            elements.append(Paragraph("FOUNDATION UNIVERSITY — OVALENS HATCHERY SYSTEM", title_style))
            elements.append(Paragraph(f"Official Candling Audit & Batch Report — {batch.batch_code}", sub_style))
            elements.append(Spacer(1, 16))

            meta_data = [
                ["Batch ID:", batch.batch_id, "Duck Breed:", batch.breed.value],
                ["Incubator:", batch.incubator_id, "Current Stage:", batch.current_stage.value],
                ["Initial Set Count:", str(batch.initial_egg_count), "Batch Status:", batch.status.value],
                ["Set Date:", batch.set_date.strftime("%Y-%m-%d %H:%M"), "Hatch Date:", batch.target_hatch_date.strftime("%Y-%m-%d %H:%M")],
                ["Hatched Count:", str(batch.hatched_count), "Unhatched Count:", str(batch.unhatched_count)]
            ]

            t_meta = Table(meta_data, colWidths=[110, 160, 110, 160])
            t_meta.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]))
            elements.append(t_meta)
            elements.append(Spacer(1, 18))

            elements.append(Paragraph("<b>Candling Milestone Sessions Summary</b>", styles["Heading3"]))
            elements.append(Spacer(1, 6))

            sess_data = [["Stage", "Operator", "Total Scanned", "Fertile", "Infertile", "Abnormal", "Avg Latency (ms)"]]
            for s in sessions:
                sess_data.append([
                    s.stage.value,
                    s.operator_name,
                    str(s.total_scanned),
                    str(s.fertile_count),
                    str(s.infertile_count),
                    str(s.abnormal_count),
                    f"{float(s.avg_inference_ms):.1f}"
                ])

            t_sess = Table(sess_data, colWidths=[70, 110, 80, 70, 70, 70, 70])
            t_sess.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#800000")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_sess)
            elements.append(Spacer(1, 24))

            elements.append(Paragraph(f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | OvaLens v2.0 Enterprise Engine", styles["Italic"]))

            doc.build(elements)
            buffer.seek(0)
            return buffer.getvalue()
        else:
            # Fallback simple text-based summary
            text_report = f"""FOUNDATION UNIVERSITY — OVALENS HATCHERY SYSTEM
Official Candling Audit & Batch Report — {batch.batch_code}
Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Batch Details:
- Batch ID: {batch.batch_id}
- Breed: {batch.breed.value}
- Incubator: {batch.incubator_id}
- Initial Set Count: {batch.initial_egg_count}
- Set Date: {batch.set_date.strftime('%Y-%m-%d %H:%M')}
- Target Hatch Date: {batch.target_hatch_date.strftime('%Y-%m-%d %H:%M')}
- Hatched Count: {batch.hatched_count}
- Unhatched Count: {batch.unhatched_count}

Sessions Recorded: {len(sessions)}
"""
            return text_report.encode("utf-8")
