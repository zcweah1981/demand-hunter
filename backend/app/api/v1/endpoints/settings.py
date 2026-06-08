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
    # Do not let a masked secret from the UI (***xxxx), or an empty secret
    # placeholder, overwrite a real stored secret. Secret-specific editors
    # use dedicated endpoints when the user intentionally clears/removes keys.
    if payload.secret and row.value and (not payload.value.strip() or payload.value.startswith("***")):
        row.secret = True
        db.merge(row)
        db.commit()
        return obj(row)
    row.value = payload.value
    row.secret = payload.secret
    db.merge(row)
    db.commit()
    return obj(row)

@router.post("/test-search")
def test_search(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.test_search_provider(db)


@router.post("/llm/models")
def llm_models(payload: schemas.LLMModelsIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    import requests
    fallback_row = None
    if payload.fallback_index is not None:
        rows = _fallbacks_raw(db)
        if 0 <= payload.fallback_index < len(rows):
            fallback_row = rows[payload.fallback_index]
    base = (payload.base_url.strip() or (fallback_row or {}).get("base_url", "") or (fallback_row or {}).get("provider", "") or services.setting(db, "LLM_PRIMARY_BASE_URL")).rstrip("/")
    if not base:
        return {"ok": False, "models": [], "error": "Base URL 不能为空"}
    url = base if base.endswith("/models") else f"{base}/models"
    headers = {"Accept": "application/json"}
    api_key = payload.api_key.strip()
    if not api_key or api_key.startswith("***"):
        api_key = (fallback_row or {}).get("api_key", "") if fallback_row else services.setting(db, "LLM_PRIMARY_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        raw = data.get("data", data if isinstance(data, list) else [])
        models = []
        for item in raw:
            if isinstance(item, dict):
                mid = item.get("id") or item.get("name") or item.get("model")
            else:
                mid = str(item)
            if mid:
                models.append(str(mid))
        return {"ok": True, "models": sorted(set(models)), "count": len(set(models))}
    except Exception as e:
        return {"ok": False, "models": [], "error": str(e)}


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
                rows = [{"url": str(x.get("url", "")).rstrip("/"), "api_token": str(x.get("api_token", "")), "use_builtin_engines": bool(x.get("use_builtin_engines", True)), "engines": str(x.get("engines", ""))} for x in data if isinstance(x, dict) and x.get("url")]
        except Exception:
            pass
    if rows:
        return rows
    legacy_token = services.setting(db, "SEARXNG_API_TOKEN") or ""
    legacy_engines = services.setting(db, "SEARXNG_ENGINES") or ""
    legacy_urls = services._rotating_values(db, "SEARXNG_URLS", "SEARXNG_URL")
    return [{"url": u.rstrip("/"), "api_token": legacy_token, "use_builtin_engines": not bool(legacy_engines), "engines": legacy_engines} for u in legacy_urls if u.strip()]

def _searxng_rows_status(rows: list[dict]) -> dict:
    return {"count": len(rows), "items": [{"index": i, "url": r.get("url", ""), "api_token": _mask_entry(r.get("api_token", "")), "has_token": bool(r.get("api_token")), "use_builtin_engines": bool(r.get("use_builtin_engines", True)), "engines": r.get("engines", "")} for i, r in enumerate(rows)]}

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
        rows.append({"url": url, "api_token": token, "use_builtin_engines": bool(item.use_builtin_engines), "engines": item.engines.strip()})
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

@router.post("/secret/reveal")
def secret_reveal(payload: schemas.SettingKeyRevealIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.get(models.Setting, payload.key)
    if not row or not row.value:
        return {"ok": False, "value": "", "error": "not found"}
    if payload.index is None:
        return {"ok": True, "value": row.value}
    values = _split_secret_values(row.value)
    if 0 <= payload.index < len(values):
        return {"ok": True, "value": values[payload.index]}
    return {"ok": False, "value": "", "error": "index out of range"}

@router.post("/searxng/reveal-token")
def searxng_reveal_token(payload: schemas.SettingKeyRevealIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = _searxng_rows_raw(db)
    idx = payload.index if payload.index is not None else -1
    if 0 <= idx < len(rows):
        return {"ok": True, "value": rows[idx].get("api_token", "")}
    return {"ok": False, "value": "", "error": "index out of range"}

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
            {"index": i, "base_url": r.get("base_url", r.get("provider", "")), "provider": r.get("provider", ""), "model": r.get("model", ""), "api_key": _mask_entry(r.get("api_key", "")), "has_key": bool(r.get("api_key", ""))}
            for i, r in enumerate(rows)
        ],
    }

@router.get("/llm/fallbacks")
def llm_fallbacks(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _fallbacks_status(_fallbacks_raw(db))

@router.post("/llm/reveal-key")
def llm_reveal_key(payload: schemas.SettingKeyRevealIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    if payload.key == "LLM_PRIMARY_API_KEY":
        return {"ok": True, "value": services.setting(db, "LLM_PRIMARY_API_KEY") or ""}
    rows = _fallbacks_raw(db)
    idx = payload.index if payload.index is not None else -1
    if 0 <= idx < len(rows):
        return {"ok": True, "value": rows[idx].get("api_key", "")}
    return {"ok": False, "value": "", "error": "index out of range"}

@router.post("/llm/fallbacks/append")
def llm_fallbacks_append(payload: schemas.LLMFallbackAppendIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = _fallbacks_raw(db)
    base_url = (payload.base_url or payload.provider).strip().rstrip("/")
    rows.append({"base_url": base_url, "provider": base_url, "model": payload.model.strip(), "api_key": payload.api_key.strip()})
    return _save_fallbacks(db, rows)

@router.post("/llm/fallbacks")
def llm_fallbacks_save(payload: schemas.LLMFallbacksIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    existing = _fallbacks_raw(db)
    rows = []
    for idx, item in enumerate(payload.fallbacks):
        base_url = item.base_url.strip().rstrip("/")
        if not base_url:
            continue
        api_key = item.api_key.strip()
        if (not api_key or api_key.startswith("***")) and idx < len(existing) and existing[idx].get("base_url", existing[idx].get("provider", "")) == base_url:
            api_key = existing[idx].get("api_key", "")
        rows.append({"base_url": base_url, "provider": base_url, "model": item.model.strip(), "api_key": api_key})
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
    health = {"searxng": [], "brave": {"configured": False, "keys": 0, "ok": False}, "tavily": {"configured": False, "keys": 0, "ok": False}, "serpapi": {"configured": False, "keys": 0, "ok": False}, "zenserp": {"configured": False, "keys": 0, "ok": False}, "scaleserp": {"configured": False, "keys": 0, "ok": False}}
    # SearXNG: test every configured URL independently.
    for endpoint in services.searxng_endpoints(db):
        base = endpoint["url"]
        started = time.time()
        try:
            headers = {"Accept": "application/json"}
            if endpoint.get("api_token"):
                headers["X-API-TOKEN"] = endpoint["api_token"]
            params={"q": "invoice calculator", "format": "json", "language": "en"}
            if not endpoint.get("use_builtin_engines", True) and endpoint.get("engines"):
                params["engines"] = endpoint["engines"]
            r = requests.get(f"{base.rstrip('/')}/search", params=params, headers=headers, timeout=12)
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
    serpapi_keys = services.rotating_api_keys(db, "SERPAPI_API_KEYS", "")
    zenserp_keys = services.rotating_api_keys(db, "ZENSERP_API_KEYS", "")
    scaleserp_keys = services.rotating_api_keys(db, "SCALESERP_API_KEYS", "")
    health["serpapi"].update({"configured": bool(serpapi_keys), "keys": len(serpapi_keys)})
    health["zenserp"].update({"configured": bool(zenserp_keys), "keys": len(zenserp_keys)})
    health["scaleserp"].update({"configured": bool(scaleserp_keys), "keys": len(scaleserp_keys)})
    if serpapi_keys:
        res = services.serpapi_search(db, "invoice calculator", limit=3)
        health["serpapi"].update({"ok": bool(res and res[0].get("engine") != "error"), "results": len(res), "sample": (res[0] if res else None)})
    if zenserp_keys:
        res = services.zenserp_search(db, "invoice calculator", limit=3)
        health["zenserp"].update({"ok": bool(res and res[0].get("engine") != "error"), "results": len(res), "sample": (res[0] if res else None)})
    if scaleserp_keys:
        res = services.scaleserp_search(db, "invoice calculator", limit=3)
        health["scaleserp"].update({"ok": bool(res and res[0].get("engine") != "error"), "results": len(res), "sample": (res[0] if res else None)})
    # Key pool status for all configured SERP providers
    health["key_pools"] = {
        "brave": services.provider_key_pool_status(db, "BRAVE_API_KEYS", "BRAVE_API_KEY"),
        "tavily": services.provider_key_pool_status(db, "TAVILY_API_KEYS", "TAVILY_API_KEY"),
        "serpapi": services.provider_key_pool_status(db, "SERPAPI_API_KEYS"),
        "zenserp": services.provider_key_pool_status(db, "ZENSERP_API_KEYS"),
        "scaleserp": services.provider_key_pool_status(db, "SCALESERP_API_KEYS"),
    }
    health["rotation_strategy"] = services.serp_rotation_strategy(db)
    health["available"] = services.available_serp_providers(db)
    return health

@router.get("/api-key-types")
def api_key_types(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    out = []
    for t in services.API_KEY_TYPES:
        key = t["setting_key"]
        row = db.get(models.Setting, key)
        values = _split_secret_values(row.value if row else "")
        pool = services.provider_key_pool_status(db, key) if key in {"BRAVE_API_KEYS","TAVILY_API_KEYS","SERPAPI_API_KEYS","ZENSERP_API_KEYS","SCALESERP_API_KEYS"} else None
        out.append({**t, "count": len(values), "items": [{"index": i, "masked": _mask_entry(v)} for i, v in enumerate(values)], "pool": pool})
    return {"types": out, "rotation_strategy": services.serp_rotation_strategy(db), "available_providers": services.available_serp_providers(db)}

@router.get("/api-key-types/{type_id}")
def api_key_type(type_id: str, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    t = services.api_key_type_by_id(type_id)
    if not t:
        return {"ok": False, "error": "unknown type"}
    row = db.get(models.Setting, t["setting_key"])
    values = _split_secret_values(row.value if row else "")
    pool = services.provider_key_pool_status(db, t["setting_key"]) if t["setting_key"] in {"BRAVE_API_KEYS","TAVILY_API_KEYS","SERPAPI_API_KEYS","ZENSERP_API_KEYS","SCALESERP_API_KEYS"} else None
    return {"ok": True, "type": {**t, "count": len(values), "items": [{"index": i, "masked": _mask_entry(v)} for i, v in enumerate(values)], "pool": pool}}

@router.post("/api-keys")
def api_key_add(payload: schemas.ApiKeyEntryIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    t = services.api_key_type_by_id(payload.type_id)
    if not t:
        return {"ok": False, "error": "unknown type"}
    value = services.format_api_key_entry(t, payload.values or {})
    if not value:
        return {"ok": False, "error": "empty credential"}
    key = t["setting_key"]
    row = db.get(models.Setting, key) or models.Setting(key=key, value="", secret=True)
    values = _split_secret_values(row.value)
    values.append(value)
    row.value = "\n".join(values)
    row.secret = True
    db.merge(row)
    db.commit()
    return api_key_type(payload.type_id, True, db)

@router.post("/api-keys/update")
def api_key_update(payload: schemas.ApiKeyEntryUpdateIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    t = services.api_key_type_by_id(payload.type_id)
    if not t:
        return {"ok": False, "error": "unknown type"}
    value = services.format_api_key_entry(t, payload.values or {})
    if not value:
        return {"ok": False, "error": "empty credential"}
    key = t["setting_key"]
    row = db.get(models.Setting, key) or models.Setting(key=key, value="", secret=True)
    values = _split_secret_values(row.value)
    if not (0 <= payload.index < len(values)):
        return {"ok": False, "error": "index out of range"}
    values[payload.index] = value
    row.value = "\n".join(values)
    row.secret = True
    db.merge(row)
    db.commit()
    return api_key_type(payload.type_id, True, db)

@router.post("/api-keys/remove")
def api_key_remove(payload: schemas.ApiKeyEntryRemoveIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    t = services.api_key_type_by_id(payload.type_id)
    if not t:
        return {"ok": False, "error": "unknown type"}
    key = t["setting_key"]
    row = db.get(models.Setting, key) or models.Setting(key=key, value="", secret=True)
    values = _split_secret_values(row.value)
    if not (0 <= payload.index < len(values)):
        return {"ok": False, "error": "index out of range"}
    values.pop(payload.index)
    row.value = "\n".join(values)
    row.secret = True
    db.merge(row)
    db.commit()
    return api_key_type(payload.type_id, True, db)
