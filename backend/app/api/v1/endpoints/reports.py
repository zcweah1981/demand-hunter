from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app import services
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/export")
def export_report(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return {"path": services.export_latest_markdown(db)}

@router.post("/export/actions")
def export_action_report(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return {"path": services.export_action_execution_markdown(db)}

@router.get("/download/actions")
def download_action_report(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    path = services.export_action_execution_markdown(db)
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename="action_execution_list.md")
