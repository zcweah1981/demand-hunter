from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("")
def list_settings(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    rows = db.query(models.Setting).order_by(models.Setting.key).all()
    out = []
    for r in rows:
        d = obj(r)
        if r.secret and r.value:
            d["value"] = "***" + r.value[-4:]
        out.append(d)
    return out

@router.post("")
def upsert_setting(payload: schemas.SettingIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.Setting, payload.key) or models.Setting(key=payload.key)
    row.value = payload.value
    row.secret = payload.secret
    db.merge(row)
    db.commit()
    return obj(row)

@router.post("/test-search")
def test_search(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.test_search_provider(db)
