from __future__ import annotations
import secrets
import threading
from typing import Any, Callable

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def set_job(job_id: str, **kwargs):
    with _lock:
        job = _jobs.get(job_id, {"id": job_id, "status": "pending", "result": None, "error": None})
        job.update(kwargs)
        _jobs[job_id] = job


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _jobs.get(job_id)


def _run_background(job_id: str, fn: Callable[..., Any], *args, **kwargs):
    from app.database import SessionLocal
    set_job(job_id, status="running")
    try:
        db = SessionLocal()
        try:
            result = fn(db, *args, **kwargs)
        finally:
            db.close()
        set_job(job_id, status="ok", result=result)
    except Exception as e:
        set_job(job_id, status="failed", error=str(e))


def start_job(fn: Callable[..., Any], *args, **kwargs) -> str:
    job_id = secrets.token_urlsafe(12)
    set_job(job_id, status="pending")
    threading.Thread(target=_run_background, args=(job_id, fn, *args), kwargs=kwargs, daemon=True).start()
    return job_id


def job_response(job_id: str) -> dict:
    return {"job_id": job_id, "status": "pending", "poll": f"/api/discovery/job/{job_id}"}
