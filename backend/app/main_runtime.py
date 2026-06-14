from __future__ import annotations
import threading
import time
from app import automation_cycle, services
from app.api.run_control import RUN_LOCK


def run_daily_background(force: bool = False):
    from app.database import SessionLocal
    if not RUN_LOCK.acquire(blocking=False):
        return {"started": False, "reason": "already_running"}
    try:
        db = SessionLocal()
        try:
            due = services.auto_due(db)
            if force or due:
                try:
                    max_seconds = int(services.setting(db, "AUTOMATION_CYCLE_MAX_SECONDS") or "300")
                except Exception:
                    max_seconds = 300
                result = automation_cycle.run_automation_cycle(db, max_seconds=max_seconds, run_legacy_daily=False)
                services.export_latest_markdown(db)
                return {"started": True, "status": "ok" if result.get("ok") else "error", "summary": result}
            return {"started": False, "reason": "not_due"}
        finally:
            db.close()
    finally:
        RUN_LOCK.release()


def start_run_thread(force: bool = False):
    if RUN_LOCK.locked():
        return {"started": False, "reason": "already_running"}
    threading.Thread(target=run_daily_background, args=(force,), daemon=True).start()
    return {"started": True, "background": True}


def auto_loop():
    while True:
        try:
            start_run_thread(force=False)
        except Exception:
            pass
        time.sleep(60)
