from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import action_requests, four_find, models, schemas
from app.api.deps import obj
from app.api.jobs import get_job
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


def _execute_four_find_action(db: Session, operation: str, reason: str, payload: dict, target_id: str | int | None = None) -> dict:
    request = action_requests.create_action_request(
        db,
        "four_find.run",
        "four_find",
        str(target_id or operation),
        requested_by="api",
        reason=reason,
        payload={"operation": operation, **payload},
    )
    execution = action_requests.execute_action_request(db, request.id)
    return {
        "ok": bool(execution.get("ok")),
        "request_id": request.id,
        "run_id": execution.get("run_id"),
        "status_url": f"/api/actions/{request.id}",
        "execution": execution,
        "result": execution.get("result"),
    }

@router.post("/expand")
def discovery_expand(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(db, "expand", "手动四找词找词", {"seed": payload.seed})

@router.post("/find-sites")
def discovery_find_sites(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(db, "find_sites", "手动四找词找站", {"seed": payload.seed})

@router.post("/site-keywords")
def discovery_site_keywords(payload: schemas.DiscoveryDomainIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(db, "site_keywords", "手动四找站找词", {"domain": payload.domain})

@router.post("/similar-sites")
def discovery_similar_sites(payload: schemas.DiscoveryDomainIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(db, "similar_sites", "手动四找站找站", {"domain": payload.domain})

@router.post("/run")
def discovery_run(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(db, "run", "手动完整四找", {"seed": payload.seed, "depth": payload.depth or 2})

@router.post("/run-and-import")
def discovery_run_and_import(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(
        db,
        "run_and_import",
        "手动完整四找并导入",
        {"seed": payload.seed, "depth": payload.depth or 2, "import_limit": payload.import_limit or 12},
    )

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
    result = _execute_four_find_action(db, "prune", "手动清理低质量四找结果", {})
    result["loop_status"] = four_find.discovery_loop_status(db)
    return result

@router.post("/recover-serp-rejects")
def discovery_recover_serp_rejects(payload: schemas.DailyRunIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(db, "recover_serp_rejects", "手动恢复 SERP 拒绝项", {"limit": payload.limit or 8})

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
    result = _execute_four_find_action(db, "import_expansion", "手动导入词找词结果", {"id": expansion_id}, target_id=expansion_id)
    if not result.get("ok"):
        raise HTTPException(404, "not found or already imported")
    return result

@router.post("/import-competitor-keyword/{ck_id}")
def discovery_import_ck(ck_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    result = _execute_four_find_action(db, "import_competitor_keyword", "手动导入站找词结果", {"id": ck_id}, target_id=ck_id)
    if not result.get("ok"):
        raise HTTPException(404, "not found or already imported")
    return result

@router.post("/import-discovered")
def discovery_import_discovered(payload: schemas.DiscoverySeedIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return _execute_four_find_action(
        db,
        "import_discovered",
        "手动导入四找已发现关键词",
        {"seed": payload.seed or "", "import_limit": payload.import_limit or 12},
    )
