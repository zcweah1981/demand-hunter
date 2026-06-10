from __future__ import annotations
import threading
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.api.run_control import RUN_LOCK
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/runs", tags=["runs"])

@router.post("/daily")
def run_daily(payload: schemas.DailyRunIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    if RUN_LOCK.locked():
        return {"started": False, "reason": "already_running"}
    def target():
        from app.database import SessionLocal
        if not RUN_LOCK.acquire(blocking=False):
            return
        local = SessionLocal()
        try:
            services.daily_run(local, payload.limit, payload.roots, use_four_find=payload.use_four_find, seeds=payload.seeds, trigger="manual_daily")
            services.export_latest_markdown(local)
        finally:
            local.close()
            RUN_LOCK.release()
    threading.Thread(target=target, daemon=True).start()
    return {"started": True, "background": True}

@router.get("")
def runs(limit: int = 20, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    limit=max(1, min(50, limit))
    return [obj(x) for x in db.query(models.RunHistory).order_by(models.RunHistory.started_at.desc()).limit(limit).all()]
