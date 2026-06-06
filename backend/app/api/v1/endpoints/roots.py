from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/roots", tags=["roots"])

@router.get("")
def roots(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    return [obj(r) for r in db.query(models.Root).order_by(models.Root.category, models.Root.term).all()]

@router.post("")
def add_root(payload: schemas.RootIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = models.Root(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return obj(row)
