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


def _split_secret_values(value: str) -> list[str]:
    import re
    return [x.strip() for x in re.split(r"[\n,]+", value or "") if x.strip()]

def _mask_entry(value: str) -> str:
    if not value:
        return ""
    return "***" + value[-4:] if len(value) > 4 else "***"

@router.get("/secret-list/{key}")
def secret_list_status(key: str, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.Setting, key)
    values = _split_secret_values(row.value if row else "")
    return {"key": key, "count": len(values), "items": [{"index": i, "masked": _mask_entry(v)} for i, v in enumerate(values)], "updated_at": row.updated_at if row else None}

@router.post("/secret-list/append")
def secret_list_append(payload: schemas.SettingKeyAppendIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.Setting, payload.key) or models.Setting(key=payload.key, value="", secret=True)
    values = _split_secret_values(row.value)
    if payload.value.strip():
        values.append(payload.value.strip())
    row.value = "\n".join(values)
    row.secret = True
    db.merge(row)
    db.commit()
    return {"key": payload.key, "count": len(values), "items": [{"index": i, "masked": _mask_entry(v)} for i, v in enumerate(values)]}

@router.post("/secret-list/clear")
def secret_list_clear(payload: schemas.SettingKeyClearIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.Setting, payload.key) or models.Setting(key=payload.key, value="", secret=True)
    row.value = ""
    row.secret = True
    db.merge(row)
    db.commit()
    return {"key": payload.key, "count": 0, "items": []}
