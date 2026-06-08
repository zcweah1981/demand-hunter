from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import collectors, models, schemas, services
from app.core.security import require_auth
from app.database import get_db
from app.main_runtime import start_run_thread

router = APIRouter(prefix="/api/autopilot", tags=["autopilot"])


def _set_setting(db: Session, key: str, value: str, secret: bool = False):
    row = db.get(models.Setting, key) or models.Setting(key=key)
    row.value = value
    row.secret = secret
    db.merge(row)


def _bool_setting(db: Session, key: str) -> bool:
    return (services.setting(db, key) or "").lower() in {"1", "true", "yes", "on"}


@router.get("/status")
def autopilot_status(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    auto = services.auto_status(db)
    providers = services.available_serp_providers(db)
    seeds = [x.strip() for x in (services.setting(db, "FOUR_FIND_AUTO_SEEDS") or "").split(",") if x.strip()]
    domains = [x.strip() for x in (services.setting(db, "FOUR_FIND_AUTO_DOMAINS") or "").replace("\n", ",").split(",") if x.strip()]
    cards = db.query(models.OpportunityCard).count()
    pending_review = db.query(models.OpportunityCard).filter(models.OpportunityCard.feedback_label == "").count()
    actions = db.query(models.OpportunityCard).filter(models.OpportunityCard.verdict == "Action").count()
    watch = db.query(models.OpportunityCard).filter(models.OpportunityCard.verdict == "Watch").count()
    discoveries = db.query(models.DiscoveryExpansion).count() + db.query(models.CompetitorKeyword).count() + db.query(models.CompetitorSite).count()
    collector_summary = collectors.collector_pool_summary(db)
    last = auto.get("last_run")
    running = bool(last and last.get("status") == "running")
    ready_checks = [
        {"key": "search", "label": "搜索源可用", "ok": bool(providers), "detail": ", ".join(providers) or "未配置 SearXNG/Brave/Tavily"},
        {"key": "seeds", "label": "自动 seeds 已配置", "ok": bool(seeds or domains), "detail": f"{len(seeds)} seeds · {len(domains)} domains"},
        {"key": "auto", "label": "自动循环已开启", "ok": bool(auto.get("enabled")), "detail": f"每 {auto.get('interval_minutes')} 分钟"},
        {"key": "four_find", "label": "四找闭环已开启", "ok": _bool_setting(db, "FOUR_FIND_AUTO_ENABLED"), "detail": "Discovery → Import → Card → Review feedback"},
        {"key": "collectors", "label": "采集器候选池已开启", "ok": _bool_setting(db, "COLLECTOR_AUTO_ENABLED"), "detail": f"new {collector_summary.get('by_status',{}).get('new',0)} · imported {collector_summary.get('by_status',{}).get('imported',0)} · rejected {collector_summary.get('by_status',{}).get('rejected',0)}"},
    ]
    ready = all(x["ok"] for x in ready_checks)
    if running:
        next_action = "系统正在跑，等结果生成后只需要复核 Watch/Action 卡。"
    elif last and isinstance(last.get("summary"), dict) and last["summary"].get("diagnosis", {}).get("next_action"):
        next_action = last["summary"]["diagnosis"]["next_action"]
    elif not ready:
        next_action = "点击“开启自动猎手”，我会补齐默认自动化配置并启动一轮。"
    elif pending_review:
        next_action = f"有 {pending_review} 张卡待复核：只需要点 Action / Watch / Reject / Block。"
    elif cards:
        next_action = "系统正常，等待下一轮自动运行；也可以手动启动一轮。"
    else:
        next_action = "系统已就绪但还没有卡片，建议立即启动一轮。"
    return {
        "ready": ready,
        "mode": "autopilot" if ready else "needs_setup",
        "running": running,
        "checks": ready_checks,
        "next_action": next_action,
        "providers": providers,
        "seeds": seeds,
        "domains": domains,
        "counts": {"discoveries": discoveries, "cards": cards, "pending_review": pending_review, "action": actions, "watch": watch},
        "collectors": collector_summary,
        "diagnosis": last.get("summary", {}).get("diagnosis") if last and isinstance(last.get("summary"), dict) else None,
        "auto": auto,
    }


@router.post("/start")
def autopilot_start(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    _set_setting(db, "AUTO_RUN_ENABLED", "true")
    _set_setting(db, "FOUR_FIND_AUTO_ENABLED", "true")
    _set_setting(db, "COLLECTOR_AUTO_ENABLED", "true")
    if not (services.setting(db, "FOUR_FIND_AUTO_SEEDS") or "").strip():
        _set_setting(db, "FOUR_FIND_AUTO_SEEDS", "invoice calculator,appointment template,compliance tracker")
    if not (services.setting(db, "AUTO_RUN_LIMIT") or "").strip():
        _set_setting(db, "AUTO_RUN_LIMIT", "12")
    if not (services.setting(db, "AUTO_RUN_INTERVAL_MINUTES") or "").strip():
        _set_setting(db, "AUTO_RUN_INTERVAL_MINUTES", "360")
    db.commit()
    started = start_run_thread(force=True)
    return {"ok": True, "started": started, "status": autopilot_status(True, db)}

@router.post("/repair")
def autopilot_repair(payload: schemas.RepairActionIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    return services.apply_repair_action(db, payload.action, source=payload.source, value=payload.value)

@router.get("/repairs")
def autopilot_repairs(limit: int = 20, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.list_repair_audits(db, limit=max(1, min(100, limit)))

@router.post("/repair/rollback")
def autopilot_repair_rollback(payload: schemas.RepairRollbackIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.rollback_repair_action(db, payload.repair_id)

@router.post("/experiment/start")
def autopilot_experiment_start(payload: schemas.RepairExperimentIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    res = services.start_repair_experiment(db, payload.action, source=payload.source, value=payload.value, force_run=payload.force_run)
    if res.get("ok") and payload.force_run:
        res["run"] = start_run_thread(force=True)
    return res

@router.get("/experiments")
def autopilot_experiments(limit: int = 20, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.list_repair_experiments(db, limit=max(1, min(100, limit)))
