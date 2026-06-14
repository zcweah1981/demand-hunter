from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import automation_executors, models

LOW_RISK_ACTIONS = {"run", "recalculate", "verify", "add_watch_target", "repair", "push"}
MEDIUM_RISK_ACTIONS = {"promote", "pause", "update_gate", "update_prd", "reject", "adjust_weight"}
HIGH_RISK_ACTIONS = {"adopt", "block", "delete", "permanent_block", "cleanup", "confirm_mvp"}


def risk_for_action(action_type: str, target_type: str = "") -> str:
    action_type = (action_type or "").strip().lower()
    if action_type in HIGH_RISK_ACTIONS:
        return "high"
    if action_type in MEDIUM_RISK_ACTIONS:
        return "medium"
    if action_type in LOW_RISK_ACTIONS:
        return "low"
    if target_type in {"opportunity_card", "mvp_project"} and action_type in {"push", "promote"}:
        return "high"
    return "medium"


def create_action_request(
    db: Session,
    action_type: str,
    target_type: str,
    target_id: str | int,
    requested_by: str = "user",
    reason: str = "",
    confirm: bool = False,
    payload: dict[str, Any] | None = None,
) -> models.ActionRequest:
    risk_level = risk_for_action(action_type, target_type)
    status = "pending"
    if risk_level == "high" and not confirm:
        status = "needs_confirmation"
    row = models.ActionRequest(
        action_type=action_type,
        target_type=target_type,
        target_id=str(target_id),
        risk_level=risk_level,
        status=status,
        requested_by=requested_by,
        reason=reason,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _audit(db: Session, request: models.ActionRequest, event_type: str, summary: str, payload: dict[str, Any] | None = None) -> models.ActionEvent:
    event = models.ActionEvent(
        request_id=request.id,
        event_type=event_type,
        target_type=request.target_type,
        target_id=request.target_id,
        summary=summary,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(event)
    return event


def execute_action_request(db: Session, request_id: int, confirm: bool = False) -> dict[str, Any]:
    request = db.get(models.ActionRequest, request_id)
    if not request:
        return {"ok": False, "reason": "not_found"}
    if request.risk_level == "high" and not confirm:
        request.status = "needs_confirmation"
        request.result_json = json.dumps({"ok": False, "reason": "confirmation_required"}, ensure_ascii=False)
        request.error_json = json.dumps({"reason": "confirmation_required"}, ensure_ascii=False)
        _audit(db, request, "confirmation_required", f"{request.action_type} requires confirmation")
        db.merge(request)
        db.commit()
        return {"ok": False, "reason": "confirmation_required", "request_id": request.id}

    started_at = datetime.utcnow()
    run = models.RunHistory(
        kind="manual_action",
        status="running",
        summary=json.dumps(
            {
                "stage": "running",
                "action_type": request.action_type,
                "target_type": request.target_type,
                "target_id": request.target_id,
                "request_id": request.id,
                "requested_by": request.requested_by,
            },
            ensure_ascii=False,
        ),
        started_at=started_at,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    request.run_id = run.id
    request.status = "running"
    request.started_at = started_at
    request.finished_at = None
    request.error_json = "{}"
    request.result_json = json.dumps({"ok": True, "status": "running", "run_id": run.id}, ensure_ascii=False)
    _audit(db, request, "running", f"Running {request.action_type}")
    db.merge(request)
    db.commit()

    result = automation_executors.execute_registered_action(
        db,
        {
            "source": "action_request",
            "action_type": request.action_type,
            "target_type": request.target_type,
            "target_id": request.target_id,
            "priority": 60.0 if request.risk_level == "low" else 40.0 if request.risk_level == "medium" else 5.0,
            "payload": {
                **(json.loads(request.payload_json or "{}") if request.payload_json else {}),
                "request_id": request.id,
                "risk_level": request.risk_level,
                "confirmed": bool(confirm),
            },
        },
        request=request,
    )
    from . import automation_cycle

    next_actions_created = automation_cycle.enqueue_next_actions(db, result, requested_by="system", run_id=run.id)
    run.status = "ok" if result.get("ok") else "failed"
    run.finished_at = datetime.utcnow()
    run.summary = json.dumps(
        {
            "stage": "finished",
            "action_type": request.action_type,
            "target_type": request.target_type,
            "target_id": request.target_id,
            "request_id": request.id,
            "requested_by": request.requested_by,
            "result": result,
            "next_actions_created": next_actions_created,
        },
        ensure_ascii=False,
    )
    db.merge(run)
    db.commit()
    return {
        "ok": bool(result.get("ok")),
        "request_id": request.id,
        "run_id": run.id,
        "risk_level": request.risk_level,
        "result": result,
        "next_actions_created": next_actions_created,
    }


def retry_action_request(db: Session, request_id: int) -> dict[str, Any]:
    request = db.get(models.ActionRequest, request_id)
    if not request:
        return {"ok": False, "reason": "not_found"}
    if request.retry_count >= request.max_retries:
        return {"ok": False, "reason": "max_retries_reached", "request_id": request.id}
    request.status = "pending"
    request.result_json = json.dumps({"ok": True, "status": "pending", "reason": "retry_requested"}, ensure_ascii=False)
    request.error_json = "{}"
    request.retry_count = (request.retry_count or 0) + 1
    request.executed_at = None
    request.started_at = None
    request.finished_at = None
    _audit(db, request, "retry_requested", f"Retry requested for {request.action_type}")
    db.merge(request)
    db.commit()
    return {"ok": True, "request_id": request.id, "status": request.status}


def cancel_action_request(db: Session, request_id: int) -> dict[str, Any]:
    request = db.get(models.ActionRequest, request_id)
    if not request:
        return {"ok": False, "reason": "not_found"}
    if request.status == "running":
        return {"ok": False, "reason": "running_action_cannot_be_cancelled"}
    request.status = "cancelled"
    request.result_json = json.dumps({"ok": True, "status": "cancelled"}, ensure_ascii=False)
    _audit(db, request, "cancelled", f"Cancelled {request.action_type}")
    db.merge(request)
    db.commit()
    return {"ok": True, "request_id": request.id, "status": request.status}
