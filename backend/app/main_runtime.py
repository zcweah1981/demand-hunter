from __future__ import annotations
import threading
import time
from app import services
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
                    limit = int(services.setting(db, "AUTO_RUN_LIMIT") or "24")
                except Exception:
                    limit = 24
                run = services.daily_run(db, limit=limit, trigger="manual_force" if force else "auto_scheduled")
                services.export_latest_markdown(db)
                return {"started": True, "run_id": run.id, "status": run.status}
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
