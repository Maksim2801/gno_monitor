from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_write
from app.db.session import get_db
from app.models import User
from app.schemas.reports import ReportCreate, ReportOut
from app.services.report_service import ReportService

router = APIRouter()


@router.get("", response_model=list[ReportOut])
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ReportService(db).list_reports()


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_write),
):
    try:
        return ReportService(db).create(payload, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = ReportService(db).get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = ReportService(db).get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if not report.file_path or not Path(report.file_path).exists():
        raise HTTPException(status_code=404, detail="Файл отчёта отсутствует")
    media = "application/pdf" if report.file_format == "pdf" else "text/csv"
    return FileResponse(
        report.file_path,
        media_type=media,
        filename=Path(report.file_path).name,
    )
