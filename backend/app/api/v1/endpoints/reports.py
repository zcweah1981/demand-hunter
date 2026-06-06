from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import services
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/export")
def export_report(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return {"path": services.export_latest_markdown(db)}
