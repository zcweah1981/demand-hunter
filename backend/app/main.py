from __future__ import annotations
import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import Base, engine, get_db
from . import models, schemas, services

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Demand Hunter API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    from .database import SessionLocal
    db=SessionLocal(); services.init_defaults(db); db.close()

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

@app.get("/api/settings")
def list_settings(db: Session=Depends(get_db)):
    services.init_defaults(db)
    rows=db.query(models.Setting).order_by(models.Setting.key).all()
    out=[]
    for r in rows:
        d=obj(r)
        if r.secret and r.value: d["value"]="***" + r.value[-4:]
        out.append(d)
    return out

@app.post("/api/settings")
def upsert_setting(payload: schemas.SettingIn, db: Session=Depends(get_db)):
    row=db.get(models.Setting, payload.key) or models.Setting(key=payload.key)
    row.value=payload.value; row.secret=payload.secret
    db.merge(row); db.commit()
    return obj(row)

@app.get("/api/roots")
def roots(db: Session=Depends(get_db)):
    services.init_defaults(db)
    return [obj(r) for r in db.query(models.Root).order_by(models.Root.category, models.Root.term).all()]

@app.post("/api/roots")
def add_root(payload: schemas.RootIn, db: Session=Depends(get_db)):
    row=models.Root(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return obj(row)

@app.post("/api/keywords/discover")
def discover(payload: schemas.DailyRunIn, db: Session=Depends(get_db)):
    return [obj(k) for k in services.discover_keywords(db, payload.limit, payload.roots)]

@app.get("/api/keywords")
def keywords(db: Session=Depends(get_db)):
    return [obj(k) for k in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(200).all()]

@app.post("/api/keywords")
def add_keyword(payload: schemas.KeywordIn, db: Session=Depends(get_db)):
    row=db.query(models.Keyword).filter_by(query=payload.query).first()
    if not row:
        row=models.Keyword(query=payload.query, source=payload.source, root_terms=json.dumps(payload.root_terms), intent=services.classify_intent(payload.query))
        db.add(row); db.commit(); db.refresh(row)
    return obj(row)

@app.get("/api/keywords/{keyword_id}")
def keyword_detail(keyword_id:int, db: Session=Depends(get_db)):
    kw=db.get(models.Keyword, keyword_id)
    if not kw: raise HTTPException(404, "keyword not found")
    return {"keyword": obj(kw), "serp": [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()], "competitors": [obj(x) for x in db.query(models.CompetitorPage).filter_by(keyword_id=keyword_id).all()], "social": [obj(x) for x in db.query(models.SocialEvidence).filter_by(keyword_id=keyword_id).all()], "cards": [obj(x) for x in db.query(models.OpportunityCard).filter_by(keyword_id=keyword_id).order_by(models.OpportunityCard.created_at.desc()).all()]}

@app.post("/api/keywords/{keyword_id}/serp/run")
def run_serp(keyword_id:int, db: Session=Depends(get_db)):
    kw=db.get(models.Keyword, keyword_id)
    if not kw: raise HTTPException(404, "keyword not found")
    return [obj(x) for x in services.run_serp(db, kw)]

@app.get("/api/keywords/{keyword_id}/serp")
def get_serp(keyword_id:int, db: Session=Depends(get_db)):
    return [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()]

@app.post("/api/cards/generate/{keyword_id}")
def generate_card(keyword_id:int, db: Session=Depends(get_db)):
    kw=db.get(models.Keyword, keyword_id)
    if not kw: raise HTTPException(404, "keyword not found")
    return obj(services.make_card(db, kw))

@app.get("/api/cards")
def cards(db: Session=Depends(get_db)):
    return [obj(x) for x in db.query(models.OpportunityCard).order_by(models.OpportunityCard.created_at.desc()).limit(100).all()]

@app.post("/api/cards/{card_id}/feedback")
def feedback(card_id:int, payload: schemas.FeedbackIn, db: Session=Depends(get_db)):
    card=db.get(models.OpportunityCard, card_id)
    if not card: raise HTTPException(404, "card not found")
    card.feedback_label=payload.label; card.feedback_note=payload.note
    db.commit(); return obj(card)

@app.post("/api/runs/daily")
def run_daily(payload: schemas.DailyRunIn, db: Session=Depends(get_db)):
    return obj(services.daily_run(db, payload.limit, payload.roots))

@app.get("/api/runs")
def runs(db: Session=Depends(get_db)):
    return [obj(x) for x in db.query(models.RunHistory).order_by(models.RunHistory.started_at.desc()).limit(50).all()]

@app.post("/api/reports/export")
def export_report(db: Session=Depends(get_db)):
    return {"path": services.export_latest_markdown(db)}
