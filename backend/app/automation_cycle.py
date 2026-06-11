from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from . import discovery_entries, models


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _action(source: str, action_type: str, target_type: str, target_id: str | int, priority: float, due_at: datetime | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "action_type": action_type,
        "target_type": target_type,
        "target_id": str(target_id),
        "priority": float(priority or 0.0),
        "due_at": due_at,
        "payload": payload or {},
    }


def collect_due_actions(db: Session, now: datetime | None = None, limit: int = 200) -> list[dict[str, Any]]:
    """Collect all due work for the unified automation cycle."""
    now = now or datetime.utcnow()
    actions: list[dict[str, Any]] = []

    entries = (
        db.query(models.CandidateEntry)
        .filter(models.CandidateEntry.status.in_(["new", "needs_evidence", "scored"]))
        .filter((models.CandidateEntry.next_due_at == None) | (models.CandidateEntry.next_due_at <= now))  # noqa: E711
        .order_by(models.CandidateEntry.priority.desc(), models.CandidateEntry.created_at.asc())
        .limit(limit)
        .all()
    )
    for entry in entries:
        actions.append(
            _action(
                "candidate_entry",
                discovery_entries.route_entry_next_action(entry),
                "candidate_entry",
                entry.id,
                entry.priority,
                entry.next_due_at,
                {"entry_type": entry.entry_type, "name": entry.name},
            )
        )

    watch_targets = (
        db.query(models.WatchTarget)
        .filter_by(status="active")
        .filter((models.WatchTarget.next_due_at == None) | (models.WatchTarget.next_due_at <= now))  # noqa: E711
        .order_by(models.WatchTarget.priority.desc(), models.WatchTarget.created_at.asc())
        .limit(limit)
        .all()
    )
    for target in watch_targets:
        actions.append(
            _action(
                "watch_target",
                "run_watch_target",
                "watch_target",
                target.id,
                target.priority,
                target.next_due_at,
                {"target_type": target.target_type, "target_key": target.target_key},
            )
        )

    requests = (
        db.query(models.ActionRequest)
        .filter_by(status="pending")
        .order_by(models.ActionRequest.created_at.asc())
        .limit(limit)
        .all()
    )
    for request in requests:
        priority = 60.0 if request.risk_level == "low" else 40.0 if request.risk_level == "medium" else 5.0
        actions.append(
            _action(
                "action_request",
                request.action_type,
                request.target_type,
                request.target_id,
                priority,
                request.created_at,
                {"request_id": request.id, "risk_level": request.risk_level},
            )
        )

    actions.sort(key=lambda item: (-(item["priority"] or 0.0), item["due_at"] or now))
    return actions[: max(1, min(500, limit))]


def execute_action(db: Session, action: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Execute a safe placeholder action and schedule the object for the next cycle."""
    now = now or datetime.utcnow()
    source = action.get("source")
    target_id = int(action.get("target_id") or 0)
    if source == "candidate_entry":
        entry = db.get(models.CandidateEntry, target_id)
        if entry:
            entry.next_due_at = now + timedelta(hours=6)
            entry.updated_at = now
            db.merge(entry)
            return {"ok": True, "action": action, "result": "candidate_entry_scheduled"}
    if source == "watch_target":
        target = db.get(models.WatchTarget, target_id)
        if target:
            target.last_run_at = now
            target.next_due_at = now + timedelta(hours=6)
            target.updated_at = now
            db.merge(target)
            return {"ok": True, "action": action, "result": "watch_target_scheduled"}
    if source == "action_request":
        request_id = int((action.get("payload") or {}).get("request_id") or 0)
        request = db.get(models.ActionRequest, request_id)
        if request:
            request.status = "executed"
            request.executed_at = now
            request.result_json = json.dumps({"ok": True, "handled_by": "automation_cycle"}, ensure_ascii=False)
            db.merge(request)
            db.add(
                models.ActionEvent(
                    request_id=request.id,
                    event_type="executed",
                    target_type=request.target_type,
                    target_id=request.target_id,
                    summary=f"Executed {request.action_type}",
                    payload_json=request.result_json,
                )
            )
            return {"ok": True, "action": action, "result": "action_request_executed"}
    return {"ok": False, "action": action, "error": "target_not_found"}


def run_automation_cycle(db: Session, now: datetime | None = None, max_seconds: int = 300, budget: dict[str, int] | None = None) -> dict[str, Any]:
    """Run one unified automation cycle."""
    now = now or datetime.utcnow()
    started = time.monotonic()
    actions = collect_due_actions(db, now=now, limit=sum((budget or {}).values()) if budget else 200)
    results = []
    for action in actions:
        if time.monotonic() - started > max_seconds:
            results.append({"ok": False, "action": action, "error": "time_budget_exceeded"})
            break
        results.append(execute_action(db, action, now=now))
    db.commit()
    serialized_results = []
    for result in results[:50]:
        item = dict(result)
        action = dict(item.get("action") or {})
        if isinstance(action.get("due_at"), datetime):
            action["due_at"] = _iso(action["due_at"])
        item["action"] = action
        serialized_results.append(item)
    summary = {
        "actions_collected": len(actions),
        "executed": sum(1 for result in results if result.get("ok")),
        "failed": sum(1 for result in results if not result.get("ok")),
        "results": serialized_results,
        "started_at": _iso(now),
    }
    row = models.RunHistory(
        kind="automation_cycle",
        status="ok" if summary["failed"] == 0 else "partial",
        summary=json.dumps(summary, ensure_ascii=False),
        started_at=now,
        finished_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    return {"ok": True, **summary}
