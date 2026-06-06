from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import schemas, services
from app.core.security import require_auth
from app.database import get_db
from app.main_runtime import start_run_thread

router = APIRouter(prefix="/api/auto", tags=["auto"])

@router.get("/status")
def auto_status(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.auto_status(db)

@router.post("/tick")
def auto_tick(payload: schemas.AutoTickIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return start_run_thread(force=bool(payload.force))
