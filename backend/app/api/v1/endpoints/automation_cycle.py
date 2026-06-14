from __future__ import annotations

import json
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import automation_cycle, models
from app.api.deps import obj
from app.api.run_control import RUN_LOCK
from app.core.security import require_auth
from app.database import SessionLocal, get_db

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
    if payload.get("background", True):
        if RUN_LOCK.locked():
            return {"started": False, "background": True, "reason": "already_running"}
        if not RUN_LOCK.acquire(blocking=False):
            return {"started": False, "background": True, "reason": "already_running"}

        max_seconds = max(1, int(payload.get("max_seconds") or 300))
        budget = payload.get("budget") or None
        run_legacy_daily = bool(payload.get("run_legacy_daily", False))
        include_default_actions = bool(payload.get("include_default_actions", True))
        now = datetime.utcnow()
        row = models.RunHistory(
            kind="automation_cycle",
            status="running",
            summary=json.dumps(
                {
                    "stage": "queued",
                    "actions_collected": 0,
                    "processed": 0,
                    "executed": 0,
                    "failed": 0,
                    "started_at": now.isoformat(),
                },
                ensure_ascii=False,
            ),
            started_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        run_id = row.id

        def target():
            local = SessionLocal()
            try:
                automation_cycle.run_automation_cycle(
                    local,
                    max_seconds=max_seconds,
                    budget=budget,
                    run_legacy_daily=run_legacy_daily,
                    include_default_actions=include_default_actions,
                    run_id=run_id,
                )
            finally:
                local.close()
                RUN_LOCK.release()

        threading.Thread(target=target, daemon=True).start()
        return {
            "started": True,
            "background": True,
            "run_id": run_id,
            "status_url": f"/api/automation-cycle/runs/{run_id}",
            "run_legacy_daily": run_legacy_daily,
            "include_default_actions": include_default_actions,
        }

    return automation_cycle.run_automation_cycle(
        db,
        max_seconds=max(1, int(payload.get("max_seconds") or 300)),
        budget=payload.get("budget") or None,
        run_legacy_daily=bool(payload.get("run_legacy_daily", False)),
        include_default_actions=bool(payload.get("include_default_actions", True)),
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


@router.get("/runs/{run_id}")
def automation_run_detail(run_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.RunHistory, run_id)
    if not row or row.kind != "automation_cycle":
        raise HTTPException(status_code=404, detail="automation run not found")
    data = obj(row)
    if isinstance(data.get("summary"), str):
        try:
            data["summary"] = json.loads(data["summary"])
        except Exception:
            pass
    actions = (
        db.query(models.ActionRequest)
        .filter_by(run_id=run_id)
        .order_by(models.ActionRequest.created_at.asc())
        .all()
    )
    action_items = []
    for action in actions:
        item = obj(action)
        for key in ("payload_json", "result_json", "error_json"):
            if isinstance(item.get(key), str):
                try:
                    item[key] = json.loads(item[key])
                except Exception:
                    pass
        action_items.append(item)
    data["actions"] = action_items
    return data
