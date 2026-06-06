from __future__ import annotations
import json, threading, time
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, get_db, configure_sqlite
from . import models, schemas, services
from .core.config import config
from .core.security import require_auth
from .api.v1.api import api_router
from .api.deps import obj

RUN_LOCK = threading.Lock()
PUBLIC_PATHS = {"/api/health", "/api/auth/login"}

configure_sqlite()
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Demand Hunter API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)

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
    if config.auto_worker_enabled:
        threading.Thread(target=_auto_loop, daemon=True).start()

@app.get("/api/health")
def health(db: Session=Depends(get_db)):
    return {"ok": True, "settings": len(db.query(models.Setting).all()), "keywords": db.query(models.Keyword).count(), "cards": db.query(models.OpportunityCard).count()}

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
