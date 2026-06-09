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

def _opportunity_group_counts(db: Session) -> dict:
    counts=services.opportunity_group_counts(db)
    counts["pending_review"] = len([c for c in services.grouped_opportunity_cards(db,"All") if (not c.feedback_label) and c.verdict in {"Action","Watch"}])
    return counts


@router.get("/status")
def autopilot_status(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    services.init_defaults(db)
    auto = services.auto_status(db)
    providers = services.available_serp_providers(db)
    seeds = [x.strip() for x in (services.setting(db, "FOUR_FIND_AUTO_SEEDS") or "").split(",") if x.strip()]
    domains = [x.strip() for x in (services.setting(db, "FOUR_FIND_AUTO_DOMAINS") or "").replace("\n", ",").split(",") if x.strip()]
    opportunity_counts = _opportunity_group_counts(db)
    cards = opportunity_counts["cards"]
    pending_review = opportunity_counts["pending_review"]
    actions = opportunity_counts["action"]
    watch = opportunity_counts["watch"]
    discoveries = db.query(models.DiscoveryExpansion).count() + db.query(models.CompetitorKeyword).count() + db.query(models.CompetitorSite).count()
    collector_summary = collectors.collector_pool_summary(db)
    experiments = services.list_repair_experiments(db, limit=5)
    active_experiment = next((x for x in experiments if x.get("status") == "running" or (x.get("effect") or {}).get("status") in {"pending", "no_baseline"}), None)
    latest_experiment = experiments[0] if experiments else None
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
        next_action = "系统正在跑；结果会进入机会列表，你可以直接调整 Watch / Action / Adopted 等状态。"
    elif active_experiment:
        next_action = f"推荐实验 #{active_experiment.get('id')} 正在等待评估；为避免变量污染，先等这一轮完成或在 /runs 放弃实验。"
    elif latest_experiment and isinstance(latest_experiment.get("effect"), dict):
        guard = (latest_experiment.get("effect") or {}).get("guard") or {}
        status = guard.get("status") or (latest_experiment.get("effect") or {}).get("status")
        if status == "rollback_recommended":
            next_action = f"上次实验 #{latest_experiment.get('id')} 让质量变差，建议回滚关联 repair。"
        elif status == "keep":
            next_action = f"上次实验 #{latest_experiment.get('id')} 改善了漏斗，建议保留这次修复并继续观察。"
        elif status == "observe":
            next_action = f"上次实验 #{latest_experiment.get('id')} 效果不明显，建议再观察一轮或手动回滚。"
        elif status == "pending":
            next_action = f"上次实验 #{latest_experiment.get('id')} 还在等待评估，先等下一轮 daily run 完成。"
        elif status == "abandoned":
            next_action = "上次实验已放弃；可以根据最新诊断运行一个新的推荐实验。"
        elif last and isinstance(last.get("summary"), dict) and last["summary"].get("diagnosis", {}).get("next_action"):
            next_action = last["summary"]["diagnosis"]["next_action"]
        else:
            next_action = guard.get("recommendation") or "系统正常，等待下一轮自动运行；也可以手动启动一轮。"
    elif last and isinstance(last.get("summary"), dict) and last["summary"].get("diagnosis", {}).get("next_action"):
        next_action = last["summary"]["diagnosis"]["next_action"]
    elif not ready:
        next_action = "点击“开启自动猎手”，我会补齐默认自动化配置并启动一轮。"
    elif pending_review:
        next_action = f"有 {pending_review} 个未定状态机会组；进入机会页调整 Watch / Action / Adopted / Reject / Block。"
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
        "counts": {"discoveries": discoveries, "cards": cards, "pending_review": pending_review, "action": actions, "watch": watch, "unit": "opportunity_group"},
        "collectors": collector_summary,
        "diagnosis": last.get("summary", {}).get("diagnosis") if last and isinstance(last.get("summary"), dict) else None,
        "active_experiment": active_experiment,
        "latest_experiment": latest_experiment,
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

@router.post("/experiment/abandon")
def autopilot_experiment_abandon(payload: schemas.RepairExperimentAbandonIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return services.abandon_repair_experiment(db, payload.experiment_id, rollback=payload.rollback)
