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

            # Query settings for unit prices
            from app.models.settings import HatcherySettingsModel
            from app.models.scan import FertilityClass
            from sqlalchemy import func
            
            settings_record = db.query(HatcherySettingsModel).first()
            penoy_price = float(settings_record.penoy_unit_price_php) if settings_record else 14.0
            duckling_price = float(settings_record.duckling_unit_price_php) if settings_record else 40.0
            kwh_rate = float(settings_record.electricity_kwh_rate_php) if settings_record else 12.5

            # Calculate total scanned across all sessions
            total_scanned = sum(s.total_scanned for s in sessions)
            total_fertile = sum(s.fertile_count for s in sessions)
            total_infertile = sum(s.infertile_count for s in sessions)
            total_abnormal = sum(s.abnormal_count for s in sessions)
            fertility_rate = round((total_fertile / total_scanned * 100), 2) if total_scanned > 0 else 0.0
            hatchability_rate = round((batch.hatched_count / batch.initial_egg_count * 100), 2) if batch.initial_egg_count > 0 and batch.hatched_count else 0.0

            penoy_salvage_php = round(total_infertile * penoy_price, 2)
            kwh_saved = round(total_infertile * 18 * 0.015, 2)
            power_saved_php = round(kwh_saved * kwh_rate, 2)

            elements = []
            elements.append(Paragraph("FOUNDATION UNIVERSITY — OVALENS HATCHERY SYSTEM", title_style))
            elements.append(Paragraph(f"Official Candling Inspection & Batch Audit Certificate — {batch.batch_code}", sub_style))
            elements.append(Spacer(1, 14))

            # Batch Metadata Table
            meta_data = [
                ["Batch ID:", batch.batch_id, "Duck Breed:", batch.breed.value],
                ["Incubator:", batch.incubator_id, "Current Stage:", batch.current_stage.value],
                ["Initial Set Eggs:", f"{batch.initial_egg_count:,}", "Batch Status:", batch.status.value],
                ["Incubation Set Date:", batch.set_date.strftime("%Y-%m-%d %H:%M"), "Target Hatch Date:", batch.target_hatch_date.strftime("%Y-%m-%d %H:%M")],
                ["Hatched Ducklings:", f"{batch.hatched_count:,}", "Unhatched Dead:", f"{batch.unhatched_count:,}"]
            ]

            t_meta = Table(meta_data, colWidths=[115, 155, 115, 155])
            t_meta.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]))
            elements.append(t_meta)
            elements.append(Spacer(1, 14))

            # Performance & Economics Summary Box
            elements.append(Paragraph("<b>Biological & Economic Yield Realization</b>", styles["Heading3"]))
            elements.append(Spacer(1, 4))
            econ_data = [
                ["Candled Fertility Rate:", f"{fertility_rate}%", "Final Hatchability:", f"{hatchability_rate}%"],
                ["Penoy Eggs Salvaged (Day 10):", f"{total_infertile:,} eggs", "Penoy Cash Recovery:", f"₱{penoy_salvage_php:,.2f}"],
                ["Thermal Power Saved:", f"{kwh_saved:.1f} kWh", "Electricity Savings:", f"₱{power_saved_php:,.2f}"],
            ]
            t_econ = Table(econ_data, colWidths=[140, 130, 140, 130])
            t_econ.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#065F46")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A7F3D0")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]))
            elements.append(t_econ)
            elements.append(Spacer(1, 14))

            # Sessions Table
            elements.append(Paragraph("<b>Candling Milestone Runs (Edge Optical Station)</b>", styles["Heading3"]))
            elements.append(Spacer(1, 4))

            sess_data = [["Stage", "Operator", "Total Scanned", "Fertile", "Infertile (Penoy)", "Abnormal", "Avg Latency"]]
            for s in sessions:
                sess_data.append([
                    s.stage.value,
                    s.operator_name,
                    str(s.total_scanned),
                    str(s.fertile_count),
                    str(s.infertile_count),
                    str(s.abnormal_count),
                    f"{float(s.avg_inference_ms):.1f} ms"
                ])

            t_sess = Table(sess_data, colWidths=[65, 115, 75, 65, 85, 65, 70])
            t_sess.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#800000")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]))
            elements.append(t_sess)
            elements.append(Spacer(1, 28))

            # Official Sign-Off Block
            sign_data = [
                ["___________________________________", "___________________________________"],
                ["Candling Shift Lead / Operator", "Hatchery Operations Manager"],
                ["Foundation University Hatchery", "Foundation University Hatchery"],
            ]
            t_sign = Table(sign_data, colWidths=[270, 270])
            t_sign.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]))
            elements.append(t_sign)
            elements.append(Spacer(1, 16))

            elements.append(Paragraph(f"Official Audit Document • Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} • OvaLens Ecosystem v2.0", styles["Italic"]))

            doc.build(elements)
            buffer.seek(0)
            return buffer.getvalue()
        else:
            # Fallback simple text-based summary
            text_report = f"""FOUNDATION UNIVERSITY — OVALENS HATCHERY SYSTEM
Official Candling Inspection & Batch Audit Certificate — {batch.batch_code}
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
