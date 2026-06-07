from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
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
def cards(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=[]
    for x in db.query(models.OpportunityCard).order_by(models.OpportunityCard.created_at.desc()).limit(100).all():
        d = obj(x)
        kw = db.get(models.Keyword, x.keyword_id)
        if kw:
            d["source_keyword"] = kw.query
            d["keyword_source"] = kw.source
            d["keyword_intent"] = kw.intent
        else:
            d["source_keyword"] = ""
            d["keyword_source"] = ""
            d["keyword_intent"] = ""
        rows.append(d)
    return rows

@router.post("/{card_id}/feedback")
def feedback(card_id: int, payload: schemas.FeedbackIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    card = db.get(models.OpportunityCard, card_id)
    if not card:
        raise HTTPException(404, "card not found")
    return obj(services.apply_feedback(db, card, payload.label, payload.note))
