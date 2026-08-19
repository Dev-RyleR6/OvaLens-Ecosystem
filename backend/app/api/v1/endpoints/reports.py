from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports & Export"])


@router.get("/batch/{batch_id}/csv", summary="Export raw batch candling scan dataset as CSV")
def export_batch_csv(batch_id: str, db: Session = Depends(get_db)):
    csv_content = ReportService.generate_batch_csv(db, batch_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={batch_id}_scans.csv"}
    )


@router.get("/batch/{batch_id}/pdf", summary="Export official Foundation University PDF candling audit report")
def export_batch_pdf(batch_id: str, db: Session = Depends(get_db)):
    pdf_bytes = ReportService.generate_batch_pdf(db, batch_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={batch_id}_audit_report.pdf"}
    )
