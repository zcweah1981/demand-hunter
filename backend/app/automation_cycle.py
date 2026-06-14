from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import automation_executors, discovery_entries, models, services


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


def _action_key(action: dict[str, Any]) -> str:
    return ":".join(
        [
            str(action.get("source") or ""),
            str(action.get("action_type") or action.get("action") or ""),
            str(action.get("target_type") or ""),
            str(action.get("target_id") or ""),
        ]
    )


def _has_open_request(db: Session, action_type: str, target_type: str, target_id: str | int) -> bool:
    return (
        db.query(models.ActionRequest.id)
        .filter_by(action_type=action_type, target_type=target_type, target_id=str(target_id))
        .filter(models.ActionRequest.status.in_(["pending", "running", "needs_confirmation"]))
        .first()
        is not None
    )


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

    keywords = (
        db.query(models.Keyword)
        .outerjoin(models.SerpResult, models.SerpResult.keyword_id == models.Keyword.id)
        .filter(models.SerpResult.id == None)  # noqa: E711
        .filter(models.Keyword.status.in_(["new", "action", "watch"]))
        .order_by(models.Keyword.score.desc(), models.Keyword.created_at.asc())
        .limit(limit)
        .all()
    )
    for keyword in keywords:
        if _has_open_request(db, "keyword.serp_analysis", "keyword", keyword.id):
            continue
        actions.append(
            _action(
                "keyword",
                "keyword.serp_analysis",
                "keyword",
                keyword.id,
                max(30.0, float(keyword.score or 0.0)),
                keyword.created_at,
                {"query": keyword.query, "source": keyword.source},
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
        try:
            request_payload = json.loads(request.payload_json or "{}") if request.payload_json else {}
        except Exception:
            request_payload = {}
        actions.append(
            _action(
                "action_request",
                request.action_type,
                request.target_type,
                request.target_id,
                priority,
                request.created_at,
                {**request_payload, "request_id": request.id, "risk_level": request.risk_level},
            )
        )

    actions.sort(key=lambda item: (-(item["priority"] or 0.0), item["due_at"] or now))
    return actions[: max(1, min(500, limit))]


def enqueue_next_actions(db: Session, result: dict[str, Any], requested_by: str = "system", run_id: int | None = None) -> int:
    """Persist executor-declared next actions into the shared ActionRequest queue."""
    next_actions = result.get("nextActions") if isinstance(result, dict) else []
    if not isinstance(next_actions, list):
        return 0
    created = 0
    for item in next_actions:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("action_type") or "").strip()
        target_type = str(item.get("target_type") or "").strip()
        target_id = str(item.get("target_id") or "").strip()
        if not action_type or not target_type or not target_id:
            continue
        exists = (
            db.query(models.ActionRequest)
            .filter_by(action_type=action_type, target_type=target_type, target_id=target_id)
            .filter(models.ActionRequest.status.in_(["pending", "running", "needs_confirmation"]))
            .first()
        )
        if exists:
            continue
        row = models.ActionRequest(
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            run_id=run_id,
            risk_level="low",
            status="pending",
            requested_by=requested_by,
            reason=str(item.get("reason") or "system_next_action"),
            payload_json=json.dumps(item.get("payload") or {}, ensure_ascii=False),
            result_json=json.dumps({"ok": True, "status": "pending", "source": "nextActions"}, ensure_ascii=False),
        )
        db.add(row)
        created += 1
    if created:
        db.commit()
    return created


def _bool_setting(db: Session, key: str, default: bool = False) -> bool:
    value = (services.setting(db, key) or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def default_cycle_actions(db: Session, now: datetime) -> list[dict[str, Any]]:
    """Create the standard executor-driven cycle actions.

    These replace the old daily_run black box as the normal automation path.
    Existing settings still decide whether collectors are active.
    """
    actions: list[dict[str, Any]] = []
    if _bool_setting(db, "COLLECTOR_AUTO_ENABLED", True):
        actions.append(
            _action(
                "automation_cycle",
                "clue_model.run",
                "clue_model",
                "all",
                95.0,
                now,
                {
                    "model": "all",
                    "limit": services.setting(db, "COLLECTOR_AUTO_LIMIT") or "24",
                    "import_limit": services.setting(db, "COLLECTOR_AUTO_IMPORT_LIMIT") or "12",
                },
            )
        )
    actions.append(
        _action(
            "automation_cycle",
            "clue.score",
            "clue_pool",
            "all",
            90.0,
            now,
            {"limit": services.setting(db, "COLLECTOR_AUTO_IMPORT_LIMIT") or "12"},
        )
    )
    return actions


def execute_action(db: Session, action: dict[str, Any], now: datetime | None = None, run_id: int | None = None) -> dict[str, Any]:
    """Execute one automation action through the shared executor registry."""
    now = now or datetime.utcnow()
    source = action.get("source")
    if source == "action_request":
        request_id = int((action.get("payload") or {}).get("request_id") or 0)
        request = db.get(models.ActionRequest, request_id)
        if request:
            try:
                stored_payload = json.loads(request.payload_json or "{}") if request.payload_json else {}
            except Exception:
                stored_payload = {}
            action["payload"] = {
                **stored_payload,
                **(action.get("payload") or {}),
                "request_id": request.id,
                "risk_level": request.risk_level,
            }
            request.run_id = run_id or request.run_id
            request.status = "running"
            request.started_at = now
            request.finished_at = None
            request.error_json = "{}"
            request.result_json = json.dumps({"ok": True, "status": "running", "handled_by": "automation_cycle"}, ensure_ascii=False)
            db.merge(request)
            result = automation_executors.execute_registered_action(db, action, request=request)
            created = enqueue_next_actions(db, result, requested_by="system", run_id=run_id)
            return {"ok": bool(result.get("ok")), "action": action, "result": result, "next_actions_created": created}
    if source in {"candidate_entry", "watch_target"}:
        target_id = int(action.get("target_id") or 0)
        if source == "candidate_entry" and not db.get(models.CandidateEntry, target_id):
            return {"ok": False, "action": action, "error": "target_not_found"}
        if source == "watch_target" and not db.get(models.WatchTarget, target_id):
            return {"ok": False, "action": action, "error": "target_not_found"}
        result = automation_executors.execute_registered_action(db, action)
        created = enqueue_next_actions(db, result, requested_by="system", run_id=run_id)
        return {"ok": bool(result.get("ok")), "action": action, "result": result, "next_actions_created": created}
    result = automation_executors.execute_registered_action(db, action)
    created = enqueue_next_actions(db, result, requested_by="system", run_id=run_id)
    return {"ok": bool(result.get("ok")), "action": action, "result": result, "next_actions_created": created}


def _serialize_action_result(result: dict[str, Any]) -> dict[str, Any]:
    item = dict(result)
    action = dict(item.get("action") or {})
    if isinstance(action.get("due_at"), datetime):
        action["due_at"] = _iso(action["due_at"])
    item["action"] = action
    return item


def _progress_summary(now: datetime, actions_total: int, results: list[dict[str, Any]], stage: str, daily_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "stage": stage,
        "actions_collected": actions_total,
        "processed": len(results),
        "executed": sum(1 for result in results if result.get("ok")),
        "failed": sum(1 for result in results if not result.get("ok")),
        "results": [_serialize_action_result(result) for result in results[-20:]],
        "started_at": _iso(now),
        "daily_run": daily_summary,
    }


def run_automation_cycle(
    db: Session,
    now: datetime | None = None,
    max_seconds: int = 300,
    budget: dict[str, int] | None = None,
    run_legacy_daily: bool = False,
    include_default_actions: bool = True,
    run_id: int | None = None,
) -> dict[str, Any]:
    """Run one unified automation cycle."""
    now = now or datetime.utcnow()
    started = time.monotonic()
    daily_summary: dict[str, Any] | None = None
    results: list[dict[str, Any]] = []
    attempted: set[str] = set()
    row = db.get(models.RunHistory, run_id) if run_id else None
    if not row:
        row = models.RunHistory(kind="automation_cycle")
        db.add(row)
    row.kind = "automation_cycle"
    row.status = "running"
    row.summary = json.dumps(_progress_summary(now, 0, results, "starting"), ensure_ascii=False)
    row.started_at = now
    row.finished_at = None
    db.commit()
    db.refresh(row)

    if run_legacy_daily:
        action = _action(
            "legacy_daily",
            "legacy.daily_run",
            "system",
            "daily_run",
            100.0,
            now,
            {"trigger": "automation_cycle", "limit": services.setting(db, "AUTO_RUN_LIMIT") or "6"},
        )
        attempted.add(_action_key(action))
        legacy_result = execute_action(db, action, now=now, run_id=row.id)
        daily_summary = legacy_result.get("result") if isinstance(legacy_result, dict) else legacy_result
        results.append(legacy_result)
        row.summary = json.dumps(_progress_summary(now, 0, results, "legacy_daily", daily_summary), ensure_ascii=False)
        db.merge(row)
        db.commit()

    limit = sum((budget or {}).values()) if budget else 200
    actions: list[dict[str, Any]] = []
    if include_default_actions and not run_legacy_daily:
        default_actions = default_cycle_actions(db, now)
        actions.extend(default_actions)
        for action in default_actions:
            attempted.add(_action_key(action))
            if time.monotonic() - started > max_seconds:
                results.append({"ok": False, "action": action, "error": "time_budget_exceeded"})
                break
            results.append(execute_action(db, action, now=now, run_id=row.id))
            row.summary = json.dumps(_progress_summary(now, len(actions), results, "running", daily_summary), ensure_ascii=False)
            db.merge(row)
            db.commit()

    for _ in range(10):
        due_actions = [action for action in collect_due_actions(db, now=now, limit=limit) if _action_key(action) not in attempted]
        if not due_actions:
            break
        actions.extend(due_actions)
        for action in due_actions:
            attempted.add(_action_key(action))
            if time.monotonic() - started > max_seconds:
                results.append({"ok": False, "action": action, "error": "time_budget_exceeded"})
                break
            results.append(execute_action(db, action, now=now, run_id=row.id))
            row.summary = json.dumps(_progress_summary(now, len(actions), results, "running", daily_summary), ensure_ascii=False)
            db.merge(row)
            db.commit()
        if time.monotonic() - started > max_seconds:
            break
    db.commit()
    summary = {
        "actions_collected": len(actions),
        "executed": sum(1 for result in results if result.get("ok")),
        "failed": sum(1 for result in results if not result.get("ok")),
        "processed": len(results),
        "results": [_serialize_action_result(result) for result in results[:50]],
        "started_at": _iso(now),
        "finished_at": _iso(datetime.utcnow()),
        "daily_run": daily_summary,
        "stage": "finished",
    }
    row.status = "ok" if summary["failed"] == 0 and (not daily_summary or daily_summary.get("ok")) else "partial"
    row.summary = json.dumps(summary, ensure_ascii=False)
    row.finished_at = datetime.utcnow()
    db.merge(row)
    db.commit()
    return {"ok": True, **summary}
