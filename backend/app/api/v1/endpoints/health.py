from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models
from app.database import get_db

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {"ok": True, "settings": len(db.query(models.Setting).all()), "keywords": db.query(models.Keyword).count(), "cards": db.query(models.OpportunityCard).count()}
