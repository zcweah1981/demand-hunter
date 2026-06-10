from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/cards", tags=["cards"])

def _card_obj(db: Session, x: models.OpportunityCard, opportunity_group: dict | None = None) -> dict:
    d = obj(x)
    kw = db.get(models.Keyword, x.keyword_id)
    if kw:
        d["source_keyword"] = kw.query
        d["keyword_source"] = kw.source
        d["keyword_intent"] = kw.intent
        d["keyword_status"] = kw.status
    d["opportunity_group"] = opportunity_group or services.opportunity_group_for_card(db, x)
    return d

@router.post("/generate/{keyword_id}")
def generate_card(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, keyword_id)
    if not kw:
        raise HTTPException(404, "keyword not found")
    return obj(services.make_card(db, kw))

@router.get("")
def cards(include_duplicates: bool = Query(False), _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=[]
    for x in db.query(models.OpportunityCard).order_by(models.OpportunityCard.created_at.desc()).limit(100).all():
        d = obj(x)
        kw = db.get(models.Keyword, x.keyword_id)
        if kw:
            if not include_duplicates and kw.status in {"duplicate", "rejected", "serp_reject", "rewrite_exhausted"} and x.verdict in {"Action", "Watch"}:
                continue
            d["source_keyword"] = kw.query
            d["keyword_source"] = kw.source
            d["keyword_intent"] = kw.intent
            d["keyword_status"] = kw.status
            try:
                meta = json.loads(kw.root_terms or "{}") if (kw.root_terms or "").strip().startswith("{") else {}
            except Exception:
                meta = {}
            lineage = {
                "candidate_id": meta.get("candidate_id"),
                "candidate_source": meta.get("candidate_source"),
                "source_url": meta.get("source_url"),
                "source_domain": meta.get("source_domain"),
                "collector_targets": [],
            }
            target_ids = list(meta.get("collector_target_ids") or [])
            if not target_ids:
                # Backfill display lineage for older imported keywords that
                # stored candidate/source metadata before target attribution
                # existed.
                source_domain = str(meta.get("source_domain") or "").strip().lower().removeprefix("www.")
                if source_domain:
                    target_ids.extend([r.id for r in db.query(models.CollectorTarget).filter_by(target_type="domain", value=source_domain).limit(6).all()])
                q = kw.query.strip().lower()
                if q:
                    target_ids.extend([r.id for r in db.query(models.CollectorTarget).filter_by(target_type="keyword", value=q).limit(6).all()])
                seen=[]
                target_ids=[x for x in target_ids if not (x in seen or seen.append(x))]
            for tid in target_ids[:12]:
                target = db.get(models.CollectorTarget, tid)
                if target:
                    lineage["collector_targets"].append({
                        "id": target.id,
                        "type": target.target_type,
                        "value": target.value,
                        "topic": target.topic,
                        "priority": target.priority,
                        "status": target.status,
                        "success_count": target.success_count,
                        "reject_count": target.reject_count,
                    })
            d["collector_lineage"] = lineage if (lineage["candidate_id"] or lineage["collector_targets"]) else None
        else:
            d["source_keyword"] = ""
            d["keyword_source"] = ""
            d["keyword_intent"] = ""
            d["keyword_status"] = ""
            d["collector_lineage"] = None
        d["opportunity_group"] = services.opportunity_group_for_card(db, x)
        rows.append(d)
    return rows

@router.get("/groups")
def card_groups(verdict: str = Query("All"), _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    if verdict not in {"All","Adopted","Action","Watch","Reject","Block"}:
        raise HTTPException(400, "invalid verdict")
    return [_card_obj(db, c, group) for c, group in services.grouped_opportunity_cards_with_groups(db, verdict)]

@router.post("/{card_id}/feedback")
def feedback(card_id: int, payload: schemas.FeedbackIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    card = db.get(models.OpportunityCard, card_id)
    if not card:
        raise HTTPException(404, "card not found")
    return obj(services.apply_feedback(db, card, payload.label, payload.note))

@router.post("/{card_id}/reanalyze")
def reanalyze(card_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    card = db.get(models.OpportunityCard, card_id)
    if not card:
        raise HTTPException(404, "card not found")
    return _card_obj(db, services.reanalyze_card_business(db, card))

@router.post("/bulk-feedback")
def bulk_feedback(payload: dict, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    ids=[int(x) for x in (payload.get("card_ids") or [])]
    label=str(payload.get("label") or "")
    note=str(payload.get("note") or "")
    if label not in {"Adopted","Action","Watch","Reject","Block"}:
        raise HTTPException(400, "invalid feedback label")
    out=[]
    for cid in ids[:100]:
        card=db.get(models.OpportunityCard, cid)
        if card:
            out.append(obj(services.apply_feedback(db, card, label, note)))
    return {"ok": True, "label": label, "updated": len(out), "cards": out}

@router.get("/{card_id}/markdown")
def card_markdown(card_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        path = services.export_card_markdown(db, card_id)
    except ValueError:
        raise HTTPException(404, "card not found")
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=f"opportunity-card-{card_id}.md")
