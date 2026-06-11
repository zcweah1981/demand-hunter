from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import automation_cycle, models
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/automation-cycle", tags=["automation-cycle"])


@router.get("/due")
def automation_due(limit: int = 200, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    actions = automation_cycle.collect_due_actions(db, limit=max(1, min(500, limit)))
    out = []
    for action in actions:
        item = dict(action)
        if item.get("due_at") is not None:
            item["due_at"] = item["due_at"].isoformat()
        out.append(item)
    return out


@router.post("/run")
def automation_run(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload = payload or {}
    return automation_cycle.run_automation_cycle(
        db,
        max_seconds=max(1, int(payload.get("max_seconds") or 300)),
        budget=payload.get("budget") or None,
    )


@router.get("/runs")
def automation_runs(limit: int = 20, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = (
        db.query(models.RunHistory)
        .filter_by(kind="automation_cycle")
        .order_by(models.RunHistory.started_at.desc())
        .limit(max(1, min(100, limit)))
        .all()
    )
    output = []
    for row in rows:
        data = obj(row)
        if isinstance(data.get("summary"), str):
            try:
                data["summary"] = json.loads(data["summary"])
            except Exception:
                pass
        output.append(data)
    return output
