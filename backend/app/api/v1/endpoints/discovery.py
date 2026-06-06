from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import four_find, models, schemas, services
from app.api.deps import obj
from app.api.jobs import get_job, job_response, start_job
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

@router.post("/expand")
def discovery_expand(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: [obj(e) for e in four_find.expand_by_suggest(db, payload.seed, services.searxng_search) + four_find.expand_by_related(db, payload.seed, services.searxng_search)])
    return job_response(job_id)

@router.post("/find-sites")
def discovery_find_sites(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: four_find.find_sites_from_keyword(db, payload.seed, services.searxng_search))
    return job_response(job_id)

@router.post("/site-keywords")
def discovery_site_keywords(payload: schemas.DiscoveryDomainIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: [obj(e) for e in four_find.find_keywords_from_site(db, payload.domain, services.searxng_search)])
    return job_response(job_id)

@router.post("/similar-sites")
def discovery_similar_sites(payload: schemas.DiscoveryDomainIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: [obj(e) for e in four_find.find_similar_sites(db, payload.domain, services.searxng_search)])
    return job_response(job_id)

@router.post("/run")
def discovery_run(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: four_find.run_four_find(db, payload.seed, services.searxng_search, depth=payload.depth or 2))
    return job_response(job_id)

@router.post("/run-and-import")
def discovery_run_and_import(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: four_find.run_four_find_and_import(db, payload.seed, services.searxng_search, depth=payload.depth or 2, import_limit=payload.import_limit or 12))
    return job_response(job_id)

@router.get("/job/{job_id}")
def discovery_job_status(job_id: str, _: bool = Depends(require_auth)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job

@router.get("/loop-status")
def discovery_loop_status(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return four_find.discovery_loop_status(db)

@router.post("/prune")
def discovery_prune(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    result = four_find.prune_low_quality_discoveries(db)
    result["loop_status"] = four_find.discovery_loop_status(db)
    return result

@router.post("/recover-serp-rejects")
def discovery_recover_serp_rejects(payload: schemas.DailyRunIn, _: bool = Depends(require_auth)):
    job_id = start_job(lambda db: services.recover_serp_rejects(db, limit=payload.limit or 8))
    return job_response(job_id)

@router.get("/expansions")
def discovery_list_expansions(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(e) for e in db.query(models.DiscoveryExpansion).order_by(models.DiscoveryExpansion.created_at.desc()).limit(200).all()]

@router.get("/competitor-keywords")
def discovery_list_ck(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(e) for e in db.query(models.CompetitorKeyword).order_by(models.CompetitorKeyword.created_at.desc()).limit(200).all()]

@router.get("/similar-sites")
def discovery_list_similar(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(e) for e in db.query(models.CompetitorSite).order_by(models.CompetitorSite.created_at.desc()).limit(200).all()]

@router.post("/import-expansion/{expansion_id}")
def discovery_import_expansion(expansion_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = four_find.import_expansion_to_keywords(db, expansion_id)
    if not kw:
        raise HTTPException(404, "not found or already imported")
    return obj(kw)

@router.post("/import-competitor-keyword/{ck_id}")
def discovery_import_ck(ck_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = four_find.import_competitor_keyword(db, ck_id)
    if not kw:
        raise HTTPException(404, "not found or already imported")
    return obj(kw)

@router.post("/import-discovered")
def discovery_import_discovered(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows = four_find.import_discovered_keywords(db, seed_keyword=payload.seed or None, limit=payload.import_limit or 12)
    return [obj(kw) for kw in rows]
