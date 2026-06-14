from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import action_requests, models, schemas
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("")
def action_create(payload: schemas.ActionRequestIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = action_requests.create_action_request(
        db,
        payload.action_type,
        payload.target_type,
        payload.target_id,
        requested_by=payload.requested_by,
        reason=payload.reason,
        confirm=payload.confirm,
        payload=payload.payload,
    )
    return obj(row)


@router.get("")
def action_list(status: str = "", limit: int = 100, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    q = db.query(models.ActionRequest)
    if status:
        q = q.filter(models.ActionRequest.status == status)
    rows = q.order_by(models.ActionRequest.created_at.desc()).limit(max(1, min(500, limit))).all()
    output = []
    for row in rows:
        data = obj(row)
        if isinstance(data.get("result_json"), str):
            try:
                data["result_json"] = json.loads(data["result_json"])
            except Exception:
                pass
        for key in ("payload_json", "error_json"):
            if isinstance(data.get(key), str):
                try:
                    data[key] = json.loads(data[key])
                except Exception:
                    pass
        output.append(data)
    return output


@router.get("/{request_id}")
def action_detail(request_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.ActionRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="action request not found")
    data = obj(row)
    for key in ("payload_json", "result_json", "error_json"):
        if isinstance(data.get(key), str):
            try:
                data[key] = json.loads(data[key])
            except Exception:
                pass
    return data


@router.post("/{request_id}/execute")
def action_execute(
    request_id: int,
    payload: schemas.ActionExecuteIn | None = None,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db),
):
    result = action_requests.execute_action_request(db, request_id, confirm=bool(payload and payload.confirm))
    if result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="action request not found")
    return result


@router.post("/{request_id}/retry")
def action_retry(request_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    result = action_requests.retry_action_request(db, request_id)
    if result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="action request not found")
    return result


@router.post("/{request_id}/cancel")
def action_cancel(request_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    result = action_requests.cancel_action_request(db, request_id)
    if result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="action request not found")
    if result.get("reason") == "running_action_cannot_be_cancelled":
        raise HTTPException(status_code=409, detail="running action cannot be cancelled")
    return result
