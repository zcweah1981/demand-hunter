from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import discovery_entries, models, schemas
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/entries", tags=["entries"])


def _entry_out(row: models.CandidateEntry) -> dict:
    data = obj(row)
    try:
        data["raw_context"] = json.loads(row.raw_context_json or "{}")
    except Exception:
        data["raw_context"] = {}
    data["next_action"] = discovery_entries.route_entry_next_action(row)
    return data


@router.get("")
def entry_list(
    limit: int = 100,
    status: str = "",
    entry_type: str = "",
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db),
):
    q = db.query(models.CandidateEntry)
    if status:
        q = q.filter(models.CandidateEntry.status == status)
    if entry_type:
        q = q.filter(models.CandidateEntry.entry_type == entry_type)
    rows = q.order_by(models.CandidateEntry.priority.desc(), models.CandidateEntry.created_at.desc()).limit(max(1, min(500, limit))).all()
    return [_entry_out(row) for row in rows]


@router.post("")
def entry_create(payload: schemas.CandidateEntryIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = discovery_entries.upsert_candidate_entry(
        db,
        payload.entry_type,
        payload.name,
        source=payload.source,
        source_role=payload.source_role,
        source_url=payload.source_url,
        raw_context=payload.raw_context,
        priority=payload.priority,
    )
    return _entry_out(row)


@router.get("/{entry_id}")
def entry_detail(entry_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.CandidateEntry, entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="entry not found")
    return _entry_out(row)


@router.post("/{entry_id}/push")
def entry_push(entry_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.CandidateEntry, entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="entry not found")
    action = discovery_entries.route_entry_next_action(row)
    row.status = "needs_evidence" if action == "create_evidence_task" else "scored"
    db.merge(row)
    db.commit()
    db.refresh(row)
    return {"entry": _entry_out(row), "action": action}


@router.get("/{entry_id}/timeline")
def entry_timeline(entry_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.CandidateEntry, entry_id)
    if not row:
        raise HTTPException(status_code=404, detail="entry not found")
    links = db.query(models.EvidenceLink).filter_by(target_type="candidate_entry", target_id=str(entry_id)).order_by(models.EvidenceLink.created_at.desc()).limit(100).all()
    out = []
    for link in links:
        evidence = db.get(models.EvidenceItem, link.evidence_id)
        out.append({"link": obj(link), "evidence": obj(evidence) if evidence else None})
    return {"entry": _entry_out(row), "timeline": out}
