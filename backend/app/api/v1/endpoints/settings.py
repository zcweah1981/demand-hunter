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

def _searxng_rows_raw(db: Session) -> list[dict]:
    import json
    rows: list[dict] = []
    row = db.get(models.Setting, "SEARXNG_ENDPOINTS")
    if row and row.value:
        try:
            data = json.loads(row.value)
            if isinstance(data, list):
                rows = [{"url": str(x.get("url", "")).rstrip("/"), "api_token": str(x.get("api_token", ""))} for x in data if isinstance(x, dict) and x.get("url")]
        except Exception:
            pass
    if rows:
        return rows
    legacy_token = services.setting(db, "SEARXNG_API_TOKEN") or ""
    legacy_urls = services._rotating_values(db, "SEARXNG_URLS", "SEARXNG_URL")
    return [{"url": u.rstrip("/"), "api_token": legacy_token} for u in legacy_urls if u.strip()]

def _searxng_rows_status(rows: list[dict]) -> dict:
    return {"count": len(rows), "items": [{"index": i, "url": r.get("url", ""), "api_token": _mask_entry(r.get("api_token", "")), "has_token": bool(r.get("api_token"))} for i, r in enumerate(rows)]}

@router.get("/searxng/endpoints")
def searxng_endpoints_status(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _searxng_rows_status(_searxng_rows_raw(db))

@router.post("/searxng/endpoints")
def searxng_endpoints_save(payload: schemas.SearxngEndpointsIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    import json
    existing = _searxng_rows_raw(db)
    rows = []
    for idx, item in enumerate(payload.endpoints):
        url = item.url.strip().rstrip("/")
        if not url:
            continue
        token = item.api_token.strip()
        if (not token or token.startswith("***")) and idx < len(existing) and existing[idx].get("url") == url:
            token = existing[idx].get("api_token", "")
        rows.append({"url": url, "api_token": token})
    row = db.get(models.Setting, "SEARXNG_ENDPOINTS") or models.Setting(key="SEARXNG_ENDPOINTS", value="[]", secret=True)
    row.value = json.dumps(rows, ensure_ascii=False)
    row.secret = True
    db.merge(row)
    db.commit()
    return _searxng_rows_status(rows)

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

@router.post("/secret-list/remove")
def secret_list_remove(payload: schemas.SettingKeyRemoveIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.Setting, payload.key) or models.Setting(key=payload.key, value="", secret=True)
    values = _split_secret_values(row.value)
    if 0 <= payload.index < len(values):
        values.pop(payload.index)
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


def _fallbacks_raw(db: Session) -> list[dict]:
    import json
    row = db.get(models.Setting, "LLM_FALLBACKS")
    if not row or not row.value:
        return []
    try:
        data = json.loads(row.value)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _save_fallbacks(db: Session, rows: list[dict]) -> dict:
    import json
    row = db.get(models.Setting, "LLM_FALLBACKS") or models.Setting(key="LLM_FALLBACKS", value="[]", secret=True)
    row.value = json.dumps(rows, ensure_ascii=False)
    row.secret = True
    db.merge(row)
    db.commit()
    return _fallbacks_status(rows)

def _fallbacks_status(rows: list[dict]) -> dict:
    return {
        "key": "LLM_FALLBACKS",
        "count": len(rows),
        "items": [
            {"index": i, "provider": r.get("provider", ""), "model": r.get("model", ""), "api_key": _mask_entry(r.get("api_key", ""))}
            for i, r in enumerate(rows)
        ],
    }

@router.get("/llm/fallbacks")
def llm_fallbacks(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _fallbacks_status(_fallbacks_raw(db))

@router.post("/llm/fallbacks/append")
def llm_fallbacks_append(payload: schemas.LLMFallbackAppendIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = _fallbacks_raw(db)
    rows.append({"provider": payload.provider.strip(), "model": payload.model.strip(), "api_key": payload.api_key.strip()})
    return _save_fallbacks(db, rows)

@router.post("/llm/fallbacks/remove")
def llm_fallbacks_remove(payload: schemas.LLMFallbackRemoveIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = _fallbacks_raw(db)
    if 0 <= payload.index < len(rows):
        rows.pop(payload.index)
    return _save_fallbacks(db, rows)

@router.post("/llm/fallbacks/clear")
def llm_fallbacks_clear(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _save_fallbacks(db, [])


@router.post("/provider-health")
def provider_health(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    import time
    import requests
    health = {"searxng": [], "brave": {"configured": False, "keys": 0, "ok": False}, "tavily": {"configured": False, "keys": 0, "ok": False}}
    # SearXNG: test every configured URL independently.
    for endpoint in services.searxng_endpoints(db):
        base = endpoint["url"]
        started = time.time()
        try:
            headers = {"Accept": "application/json"}
            if endpoint.get("api_token"):
                headers["X-API-TOKEN"] = endpoint["api_token"]
            r = requests.get(f"{base.rstrip('/')}/search", params={"q": "invoice calculator", "format": "json", "language": "en", "engines": services.setting(db, "SEARXNG_ENGINES") or "bing"}, headers=headers, timeout=12)
            r.raise_for_status()
            data = r.json()
            health["searxng"].append({"url": base, "ok": True, "elapsed_ms": int((time.time()-started)*1000), "results": len(data.get("results", []))})
        except Exception as e:
            health["searxng"].append({"url": base, "ok": False, "elapsed_ms": int((time.time()-started)*1000), "error": str(e)})
    brave_keys = services.rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")
    tavily_keys = services.rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY")
    health["brave"].update({"configured": bool(brave_keys), "keys": len(brave_keys)})
    health["tavily"].update({"configured": bool(tavily_keys), "keys": len(tavily_keys)})
    if brave_keys:
        res = services.brave_search(db, "invoice calculator", limit=3)
        health["brave"].update({"ok": bool(res and res[0].get("engine") != "error"), "results": len(res), "sample": (res[0] if res else None)})
    if tavily_keys:
        res = services.tavily_search(db, "invoice calculator", limit=3)
        health["tavily"].update({"ok": bool(res and res[0].get("engine") != "error"), "results": len(res), "sample": (res[0] if res else None)})
    health["available"] = services.available_serp_providers(db)
    return health
