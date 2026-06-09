from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
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

@router.get("/summary")
def collector_summary(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_pool_summary(db)

@router.get("/targets")
def collector_targets(limit: int = 120, status: str = "active", _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    q = db.query(models.CollectorTarget)
    if status:
        q = q.filter(models.CollectorTarget.status == status)
    return [obj(r) for r in q.order_by(models.CollectorTarget.priority.desc(), models.CollectorTarget.created_at.desc()).limit(limit).all()]

@router.post("/targets/refresh")
def collector_targets_refresh(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.refresh_collector_targets_from_cards(db)

@router.post("/targets/health")
def collector_targets_health(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.apply_collector_target_health(db)

@router.get("/targets/segments")
def collector_targets_segments(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_target_segments(db)

@router.get("/budget/next")
def collector_budget_next(limit: int = 24, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_next_budget(db, limit=max(1, limit))

@router.get("/runs")
def collector_runs(limit: int = 10, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.RunHistory).filter_by(kind='collector_autopilot').order_by(models.RunHistory.started_at.desc()).limit(max(1, min(50, limit))).all()
    return [obj(r) for r in rows]

@router.get("/roi")
def collector_roi(limit: int = 12, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_roi_stats(db, limit=max(1, min(50, limit)))

@router.get("/roi/recommendations")
def collector_roi_recommendations(limit: int = 12, min_runs: int = 2, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_roi_weight_recommendations(db, limit=max(1, min(50, limit)), min_runs=max(1, min_runs))

@router.post("/roi/apply")
def collector_roi_apply(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    return collectors.apply_collector_roi_weight_recommendations(db, limit=max(1, min(50, int(payload.get('limit') or 12))), min_runs=max(1, int(payload.get('min_runs') or 2)))

@router.get("/roi/applications")
def collector_roi_applications(limit: int = 10, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.RunHistory).filter_by(kind='collector_roi_weights').order_by(models.RunHistory.started_at.desc()).limit(max(1, min(50, limit))).all()
    return [obj(r) for r in rows]

@router.post("/targets/{target_id}/status")
def collector_target_status(target_id: int, payload: dict, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row=db.get(models.CollectorTarget, target_id)
    if not row: raise HTTPException(status_code=404, detail="target not found")
    status=str(payload.get('status') or '').strip()
    if status not in {'active','cooldown','rejected','exhausted'}:
        raise HTTPException(status_code=400, detail="invalid status")
    row.status=status
    if status=='active':
        row.reject_count=0
    if payload.get('note'):
        row.notes=((row.notes or '') + ' | ' + str(payload.get('note'))[:160])[:800]
    db.merge(row); db.commit(); db.refresh(row)
    return obj(row)

@router.get("/targets/{target_id}/outputs")
def collector_target_outputs(target_id: int, limit: int = 80, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    target=db.get(models.CollectorTarget, target_id)
    if not target: raise HTTPException(status_code=404, detail="target not found")
    needle=f'"collector_target_ids":'
    candidates=[]
    for c in db.query(models.CandidateKeyword).order_by(models.CandidateKeyword.created_at.desc()).limit(800).all():
        try: ev=json.loads(c.evidence_json or '{}')
        except Exception: ev={}
        ids=ev.get('collector_target_ids') or []
        if target_id in ids:
            candidates.append({**obj(c), 'evidence': ev})
            if len(candidates)>=limit: break
    keywords=[]
    for kw in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(800).all():
        try: meta=json.loads(kw.root_terms or '{}') if (kw.root_terms or '').strip().startswith('{') else {}
        except Exception: meta={}
        ids=meta.get('collector_target_ids') or []
        if target_id in ids:
            cards=[]
            for card in db.query(models.OpportunityCard).filter_by(keyword_id=kw.id).order_by(models.OpportunityCard.created_at.desc()).all():
                cards.append(obj(card))
            keywords.append({**obj(kw), 'root_meta': meta, 'cards': cards})
            if len(keywords)>=limit: break
    return {'target': obj(target), 'candidates': candidates, 'keywords': keywords, 'cards': [card for kw in keywords for card in kw.get('cards', [])]}

@router.post("/autopilot/run")
def collector_autopilot_run(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.run_collector_autopilot(db, limit=max(1, payload.limit), import_limit=max(1, payload.limit // 2 or 1))

@router.post("/sitemap/run")
def sitemap_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    return collectors.run_sitemap_watcher(db, domains, payload.max_urls_per_domain, payload.only_new)

@router.post("/domain-web/run")
def domain_web_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    return collectors.run_domain_web_collector(db, domains, max_pages_per_domain=min(12, max(1, payload.max_urls_per_domain // 10)))

@router.post("/alternatives/run")
def alternatives_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    return collectors.run_alternatives_collector(db, domains)

@router.post("/suggest/run")
def suggest_run(payload: schemas.CollectorSuggestIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    seeds=[s.strip() for s in payload.seeds if s.strip()]
    return collectors.run_suggest_collector(db, seeds)

@router.post("/advanced-search/run")
def advanced_search_run(payload: schemas.CollectorAdvancedSearchIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    roots=[x.strip() for x in payload.roots if x.strip()]
    domains=[x.strip() for x in payload.domains if x.strip()]
    return collectors.run_advanced_search_collector(db, roots, domains, payload.days, payload.limit_per_query)

@router.post("/source-radar/run")
def source_radar_run(payload: schemas.CollectorSourceRadarIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    seeds=[x.strip() for x in payload.seeds if x.strip()]
    return collectors.run_source_radar(db, seeds, payload.limit_per_seed)

@router.post("/hot-topic/run")
def hot_topic_run(payload: schemas.CollectorSuggestIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    topics=[x.strip() for x in payload.seeds if x.strip()]
    return collectors.run_hot_topic_collector(db, topics or None)

@router.post("/candidates/clean")
def candidate_clean(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.clean_candidate_pool(db, max(1, payload.limit))

@router.post("/candidates/import")
def candidate_import(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.import_candidates_to_keywords(db, payload.limit)
