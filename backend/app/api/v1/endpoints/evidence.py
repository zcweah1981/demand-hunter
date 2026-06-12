from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import evidence_models, evidence_system, models, schemas
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("")
def evidence_list(limit: int = 100, source_type: str = "", _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    q = db.query(models.EvidenceItem)
    if source_type:
        q = q.filter(models.EvidenceItem.source_type == source_type)
    rows = q.order_by(models.EvidenceItem.captured_at.desc()).limit(max(1, min(500, limit))).all()
    return [obj(row) for row in rows]


@router.post("")
def evidence_create(payload: schemas.EvidenceItemIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = evidence_system.create_evidence_item(
        db,
        source_type=payload.source_type,
        source_name=payload.source_name,
        url=payload.url,
        title=payload.title,
        summary=payload.summary,
        raw_excerpt=payload.raw_excerpt,
        raw_json=payload.raw_json,
        confidence=payload.confidence,
    )
    return obj(row)


@router.get("/derived")
def derived_entries(limit: int = 100, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = (
        db.query(models.CandidateEntry)
        .filter(models.CandidateEntry.source_role == "evidence")
        .order_by(models.CandidateEntry.created_at.desc())
        .limit(max(1, min(500, limit)))
        .all()
    )
    return [obj(row) for row in rows]


@router.get("/models")
def evidence_model_overview(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return evidence_models.model_overview(db)


@router.get("/models/{model_id}")
def evidence_model_detail(model_id: str, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    detail = evidence_models.model_detail(db, model_id)
    if not detail:
        raise HTTPException(status_code=404, detail="evidence model not found")
    return detail


@router.get("/targets/{target_type}/{target_id}/timeline")
def target_timeline(
    target_type: str,
    target_id: str,
    limit: int = 100,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db),
):
    return evidence_system.timeline_for_target(db, target_type, target_id, limit=limit)


@router.get("/{evidence_id}")
def evidence_detail(evidence_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.EvidenceItem, evidence_id)
    if not row:
        raise HTTPException(status_code=404, detail="evidence not found")
    links = db.query(models.EvidenceLink).filter_by(evidence_id=evidence_id).order_by(models.EvidenceLink.created_at.desc()).all()
    return {"evidence": obj(row), "links": [obj(link) for link in links]}


@router.post("/{evidence_id}/links")
def evidence_link(evidence_id: int, payload: schemas.EvidenceLinkIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    if not db.get(models.EvidenceItem, evidence_id):
        raise HTTPException(status_code=404, detail="evidence not found")
    link = evidence_system.link_evidence(
        db,
        evidence_id=evidence_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        relation_type=payload.relation_type,
        relation_reason=payload.relation_reason,
        created_by=payload.created_by,
    )
    return obj(link)


@router.post("/{evidence_id}/derived-entry")
def evidence_derived_entry(
    evidence_id: int,
    payload: schemas.EvidenceDerivedEntryIn,
    _: bool = Depends(require_auth),
    db: Session = Depends(get_db),
):
    try:
        entry = evidence_system.create_derived_entry_from_evidence(
            db,
            evidence_id=evidence_id,
            entry_type=payload.entry_type,
            name=payload.name,
            relation_reason=payload.relation_reason,
            source_role=payload.source_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return obj(entry)
