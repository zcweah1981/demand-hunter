from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/cards", tags=["cards"])

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
        else:
            d["source_keyword"] = ""
            d["keyword_source"] = ""
            d["keyword_intent"] = ""
            d["keyword_status"] = ""
        rows.append(d)
    return rows

@router.post("/{card_id}/feedback")
def feedback(card_id: int, payload: schemas.FeedbackIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    card = db.get(models.OpportunityCard, card_id)
    if not card:
        raise HTTPException(404, "card not found")
    return obj(services.apply_feedback(db, card, payload.label, payload.note))

@router.get("/{card_id}/markdown")
def card_markdown(card_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        path = services.export_card_markdown(db, card_id)
    except ValueError:
        raise HTTPException(404, "card not found")
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=f"opportunity-card-{card_id}.md")
