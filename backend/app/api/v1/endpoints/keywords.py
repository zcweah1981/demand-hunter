from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/keywords", tags=["keywords"])

@router.post("/discover")
def discover(payload: schemas.DailyRunIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    if payload.use_four_find:
        return [obj(k) for k in services.discover_keywords_four_find(db, payload.limit, payload.seeds)]
    return [obj(k) for k in services.discover_keywords(db, payload.limit, payload.roots)]

@router.get("")
def keywords(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(k) for k in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(200).all()]

@router.post("")
def add_keyword(payload: schemas.KeywordIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.query(models.Keyword).filter_by(query=payload.query).first()
    if not row:
        row = models.Keyword(query=payload.query, source=payload.source, root_terms=json.dumps(payload.root_terms), intent=services.classify_intent(payload.query))
        db.add(row)
        db.commit()
        db.refresh(row)
    return obj(row)

@router.get("/{keyword_id}")
def keyword_detail(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, keyword_id)
    if not kw:
        raise HTTPException(404, "keyword not found")
    return {
        "keyword": obj(kw),
        "serp": [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()],
        "competitors": [obj(x) for x in db.query(models.CompetitorPage).filter_by(keyword_id=keyword_id).all()],
        "social": [obj(x) for x in db.query(models.SocialEvidence).filter_by(keyword_id=keyword_id).all()],
        "cards": [obj(x) for x in db.query(models.OpportunityCard).filter_by(keyword_id=keyword_id).order_by(models.OpportunityCard.created_at.desc()).all()],
    }

@router.post("/{keyword_id}/serp/run")
def run_serp(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, keyword_id)
    if not kw:
        raise HTTPException(404, "keyword not found")
    return [obj(x) for x in services.run_serp(db, kw)]

@router.get("/{keyword_id}/serp")
def get_serp(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()]
