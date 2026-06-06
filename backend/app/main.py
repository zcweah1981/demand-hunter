from __future__ import annotations
import json, os, hmac, secrets, threading, time
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, get_db, configure_sqlite
from . import four_find, models, schemas, services

AUTH_TOKEN = os.environ.get("DEMAND_HUNTER_AUTH_TOKEN", "") or secrets.token_urlsafe(32)
AUTH_PASSWORD = os.environ.get("DEMAND_HUNTER_PASSWORD", "")
RUN_LOCK = threading.Lock()
PUBLIC_PATHS = {"/api/health", "/api/auth/login"}

# ---- Discovery job registry (in-memory, API-first async pattern) ----
_discovery_jobs: dict[str, dict] = {}
_discovery_lock = threading.Lock()

def _set_job(job_id: str, **kwargs):
    with _discovery_lock:
        job = _discovery_jobs.get(job_id, {"id": job_id, "status": "pending", "result": None, "error": None})
        job.update(kwargs)
        _discovery_jobs[job_id] = job

def _run_discovery_background(job_id: str, fn, *args, **kwargs):
    from .database import SessionLocal
    _set_job(job_id, status="running")
    try:
        db = SessionLocal()
        try:
            result = fn(db, *args, **kwargs)
        finally:
            db.close()
        _set_job(job_id, status="ok", result=result)
    except Exception as e:
        _set_job(job_id, status="failed", error=str(e))

def _start_discovery_job(fn, *args, **kwargs) -> str:
    job_id = secrets.token_urlsafe(12)
    _set_job(job_id, status="pending")
    threading.Thread(target=_run_discovery_background, args=(job_id, fn, *args), kwargs=kwargs, daemon=True).start()
    return job_id

def require_auth(authorization: str | None = Header(default=None)):
    if not AUTH_PASSWORD:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = authorization.split(" ", 1)[1]
    if not hmac.compare_digest(token, AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="unauthorized")
    return True

configure_sqlite()
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Demand Hunter API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def _run_daily_background(force: bool = False):
    from .database import SessionLocal
    if not RUN_LOCK.acquire(blocking=False):
        return {"started": False, "reason": "already_running"}
    try:
        db = SessionLocal()
        try:
            if force or services.auto_due(db):
                try: limit = int(services.setting(db, "AUTO_RUN_LIMIT") or "24")
                except Exception: limit = 24
                run = services.daily_run(db, limit=limit)
                services.export_latest_markdown(db)
                return {"started": True, "run_id": run.id, "status": run.status}
            return {"started": False, "reason": "not_due"}
        finally:
            db.close()
    finally:
        RUN_LOCK.release()

def _start_run_thread(force: bool = False):
    if RUN_LOCK.locked():
        return {"started": False, "reason": "already_running"}
    threading.Thread(target=_run_daily_background, args=(force,), daemon=True).start()
    return {"started": True, "background": True}

def _auto_loop():
    while True:
        try:
            _start_run_thread(force=False)
        except Exception:
            pass
        time.sleep(60)

@app.on_event("startup")
def startup():
    from .database import SessionLocal
    db=SessionLocal(); services.init_defaults(db); db.close()
    if (os.environ.get("DEMAND_HUNTER_AUTO_WORKER", "true").lower() in {"1","true","yes","on"}):
        threading.Thread(target=_auto_loop, daemon=True).start()

def obj(row):
    d={c.name:getattr(row,c.name) for c in row.__table__.columns}
    for k in ["root_terms","gap_tags","weakness_tags","pain_tags","evidence_json","risks","summary"]:
        if k in d and isinstance(d[k], str):
            try: d[k]=json.loads(d[k])
            except Exception: pass
    return d

@app.get("/api/health")
def health(db: Session=Depends(get_db)):
    return {"ok": True, "settings": len(db.query(models.Setting).all()), "keywords": db.query(models.Keyword).count(), "cards": db.query(models.OpportunityCard).count()}

# ---- Four-Find Discovery ----

@app.post("/api/discovery/expand")
def discovery_expand(payload: schemas.DiscoverySeedIn, _: bool=Depends(require_auth)):
    """词找词: expand a seed keyword"""
    job_id = _start_discovery_job(
        lambda db: [obj(e) for e in four_find.expand_by_suggest(db, payload.seed, services.searxng_search) + four_find.expand_by_related(db, payload.seed, services.searxng_search)]
    )
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}

@app.post("/api/discovery/find-sites")
def discovery_find_sites(payload: schemas.DiscoverySeedIn, _: bool=Depends(require_auth)):
    """词找站: find sites from a keyword"""
    job_id = _start_discovery_job(
        lambda db: four_find.find_sites_from_keyword(db, payload.seed, services.searxng_search)
    )
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}

@app.post("/api/discovery/site-keywords")
def discovery_site_keywords(payload: schemas.DiscoveryDomainIn, _: bool=Depends(require_auth)):
    """站找词: reverse discover keywords from a competitor domain"""
    job_id = _start_discovery_job(
        lambda db: [obj(e) for e in four_find.find_keywords_from_site(db, payload.domain, services.searxng_search)]
    )
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}

@app.post("/api/discovery/similar-sites")
def discovery_similar_sites(payload: schemas.DiscoveryDomainIn, _: bool=Depends(require_auth)):
    """站找站: find similar sites"""
    job_id = _start_discovery_job(
        lambda db: [obj(e) for e in four_find.find_similar_sites(db, payload.domain, services.searxng_search)]
    )
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}

@app.post("/api/discovery/run")
def discovery_run(payload: schemas.DiscoverySeedIn, _: bool=Depends(require_auth)):
    """Run full four-find pipeline"""
    job_id = _start_discovery_job(
        lambda db: four_find.run_four_find(db, payload.seed, services.searxng_search, depth=payload.depth or 2)
    )
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}

@app.post("/api/discovery/run-and-import")
def discovery_run_and_import(payload: schemas.DiscoverySeedIn, _: bool=Depends(require_auth)):
    """Run full Four-Find pipeline and import discoveries into the main keyword flow."""
    job_id = _start_discovery_job(
        lambda db: four_find.run_four_find_and_import(db, payload.seed, services.searxng_search, depth=payload.depth or 2, import_limit=payload.import_limit or 12)
    )
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}

@app.get("/api/discovery/job/{job_id}")
def discovery_job_status(job_id: str, _: bool=Depends(require_auth)):
    """Poll discovery job status."""
    with _discovery_lock:
        job = _discovery_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job

@app.get("/api/discovery/loop-status")
def discovery_loop_status(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    """Four-Find closed-loop dashboard data."""
    return four_find.discovery_loop_status(db)

@app.get("/api/discovery/expansions")
def discovery_list_expansions(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(e) for e in db.query(models.DiscoveryExpansion).order_by(models.DiscoveryExpansion.created_at.desc()).limit(200).all()]

@app.get("/api/discovery/competitor-keywords")
def discovery_list_ck(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(e) for e in db.query(models.CompetitorKeyword).order_by(models.CompetitorKeyword.created_at.desc()).limit(200).all()]

@app.get("/api/discovery/similar-sites")
def discovery_list_similar(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(e) for e in db.query(models.CompetitorSite).order_by(models.CompetitorSite.created_at.desc()).limit(200).all()]

@app.post("/api/discovery/import-expansion/{expansion_id}")
def discovery_import_expansion(expansion_id: int, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    kw = four_find.import_expansion_to_keywords(db, expansion_id)
    if not kw: raise HTTPException(404, "not found or already imported")
    return obj(kw)

@app.post("/api/discovery/import-competitor-keyword/{ck_id}")
def discovery_import_ck(ck_id: int, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    kw = four_find.import_competitor_keyword(db, ck_id)
    if not kw: raise HTTPException(404, "not found or already imported")
    return obj(kw)

@app.post("/api/discovery/import-discovered")
def discovery_import_discovered(payload: schemas.DiscoverySeedIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    rows = four_find.import_discovered_keywords(db, seed_keyword=payload.seed or None, limit=payload.import_limit or 12)
    return [obj(kw) for kw in rows]


@app.post("/api/auth/login")
def login(payload: schemas.AuthLoginIn):
    if not AUTH_PASSWORD:
        return {"token": AUTH_TOKEN, "auth_enabled": False}
    if not hmac.compare_digest(payload.password, AUTH_PASSWORD):
        raise HTTPException(status_code=401, detail="invalid password")
    return {"token": AUTH_TOKEN, "auth_enabled": True}

@app.get("/api/auth/me")
def me(_: bool=Depends(require_auth)):
    return {"ok": True, "auth_enabled": bool(AUTH_PASSWORD)}

@app.get("/api/settings")
def list_settings(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    services.init_defaults(db)
    rows=db.query(models.Setting).order_by(models.Setting.key).all()
    out=[]
    for r in rows:
        d=obj(r)
        if r.secret and r.value: d["value"]="***" + r.value[-4:]
        out.append(d)
    return out

@app.post("/api/settings")
def upsert_setting(payload: schemas.SettingIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    row=db.get(models.Setting, payload.key) or models.Setting(key=payload.key)
    row.value=payload.value; row.secret=payload.secret
    db.merge(row); db.commit()
    return obj(row)

@app.get("/api/roots")
def roots(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    services.init_defaults(db)
    return [obj(r) for r in db.query(models.Root).order_by(models.Root.category, models.Root.term).all()]

@app.post("/api/roots")
def add_root(payload: schemas.RootIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    row=models.Root(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return obj(row)

@app.post("/api/keywords/discover")
def discover(payload: schemas.DailyRunIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    if payload.use_four_find:
        return [obj(k) for k in services.discover_keywords_four_find(db, payload.limit, payload.seeds)]
    return [obj(k) for k in services.discover_keywords(db, payload.limit, payload.roots)]

@app.get("/api/keywords")
def keywords(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(k) for k in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(200).all()]

@app.post("/api/keywords")
def add_keyword(payload: schemas.KeywordIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    row=db.query(models.Keyword).filter_by(query=payload.query).first()
    if not row:
        row=models.Keyword(query=payload.query, source=payload.source, root_terms=json.dumps(payload.root_terms), intent=services.classify_intent(payload.query))
        db.add(row); db.commit(); db.refresh(row)
    return obj(row)

@app.get("/api/keywords/{keyword_id}")
def keyword_detail(keyword_id:int, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    kw=db.get(models.Keyword, keyword_id)
    if not kw: raise HTTPException(404, "keyword not found")
    return {"keyword": obj(kw), "serp": [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()], "competitors": [obj(x) for x in db.query(models.CompetitorPage).filter_by(keyword_id=keyword_id).all()], "social": [obj(x) for x in db.query(models.SocialEvidence).filter_by(keyword_id=keyword_id).all()], "cards": [obj(x) for x in db.query(models.OpportunityCard).filter_by(keyword_id=keyword_id).order_by(models.OpportunityCard.created_at.desc()).all()]}

@app.post("/api/keywords/{keyword_id}/serp/run")
def run_serp(keyword_id:int, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    kw=db.get(models.Keyword, keyword_id)
    if not kw: raise HTTPException(404, "keyword not found")
    return [obj(x) for x in services.run_serp(db, kw)]

@app.get("/api/keywords/{keyword_id}/serp")
def get_serp(keyword_id:int, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()]

@app.post("/api/cards/generate/{keyword_id}")
def generate_card(keyword_id:int, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    kw=db.get(models.Keyword, keyword_id)
    if not kw: raise HTTPException(404, "keyword not found")
    return obj(services.make_card(db, kw))

@app.get("/api/cards")
def cards(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(x) for x in db.query(models.OpportunityCard).order_by(models.OpportunityCard.created_at.desc()).limit(100).all()]

@app.post("/api/cards/{card_id}/feedback")
def feedback(card_id:int, payload: schemas.FeedbackIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    card=db.get(models.OpportunityCard, card_id)
    if not card: raise HTTPException(404, "card not found")
    return obj(services.apply_feedback(db, card, payload.label, payload.note))

@app.post("/api/runs/daily")
def run_daily(payload: schemas.DailyRunIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    if RUN_LOCK.locked():
        return {"started": False, "reason": "already_running"}
    def target():
        from .database import SessionLocal
        if not RUN_LOCK.acquire(blocking=False): return
        local = SessionLocal()
        try:
            run = services.daily_run(local, payload.limit, payload.roots, use_four_find=payload.use_four_find, seeds=payload.seeds)
            services.export_latest_markdown(local)
        finally:
            local.close(); RUN_LOCK.release()
    threading.Thread(target=target, daemon=True).start()
    return {"started": True, "background": True}

@app.get("/api/runs")
def runs(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return [obj(x) for x in db.query(models.RunHistory).order_by(models.RunHistory.started_at.desc()).limit(50).all()]


@app.post("/api/settings/test-search")
def test_search(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return services.test_search_provider(db)

@app.get("/api/auto/status")
def auto_status(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return services.auto_status(db)

@app.post("/api/auto/tick")
def auto_tick(payload: schemas.AutoTickIn, _: bool=Depends(require_auth), db: Session=Depends(get_db)):
    if payload.force:
        return _start_run_thread(force=True)
    return _start_run_thread(force=False)

@app.post("/api/reports/export")
def export_report(_: bool=Depends(require_auth), db: Session=Depends(get_db)):
    return {"path": services.export_latest_markdown(db)}
