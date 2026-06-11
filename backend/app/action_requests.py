from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import models

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
        _audit(db, request, "confirmation_required", f"{request.action_type} requires confirmation")
        db.merge(request)
        db.commit()
        return {"ok": False, "reason": "confirmation_required", "request_id": request.id}

    now = datetime.utcnow()
    request.status = "executed"
    request.executed_at = now
    result = {"ok": True, "handled_by": "action_requests", "confirmed": bool(confirm)}
    request.result_json = json.dumps(result, ensure_ascii=False)
    _audit(db, request, "executed", f"Executed {request.action_type}", result)
    db.merge(request)
    db.commit()
    return {"ok": True, "request_id": request.id, "risk_level": request.risk_level}
