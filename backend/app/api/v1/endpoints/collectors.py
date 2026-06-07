from __future__ import annotations
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import collectors, models, schemas
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/collectors", tags=["collectors"])

@router.get("/candidates")
def candidate_list(limit: int = 100, status: str = "new", _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    q = db.query(models.CandidateKeyword)
    if status:
        q = q.filter(models.CandidateKeyword.status == status)
    rows = q.order_by(models.CandidateKeyword.score.desc(), models.CandidateKeyword.created_at.desc()).limit(limit).all()
    out=[]
    for r in rows:
        d=obj(r)
        try: d["evidence"] = json.loads(r.evidence_json or "{}")
        except Exception: d["evidence"] = {}
        out.append(d)
    return out

@router.post("/sitemap/run")
def sitemap_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    return collectors.run_sitemap_watcher(db, domains, payload.max_urls_per_domain)

@router.post("/suggest/run")
def suggest_run(payload: schemas.CollectorSuggestIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    seeds=[s.strip() for s in payload.seeds if s.strip()]
    return collectors.run_suggest_collector(db, seeds)

@router.post("/candidates/import")
def candidate_import(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.import_candidates_to_keywords(db, payload.limit)
