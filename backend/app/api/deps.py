from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import Any


def obj(row: Any) -> dict:
    """Serialize SQLAlchemy row and parse JSON-encoded columns used by the API."""
    d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            # Datetimes in this app are stored as naive UTC. API records are
            # user-facing, so emit explicit Beijing time instead of leaking UTC
            # or relying on browser default timezone parsing.
            d[k] = (v + timedelta(hours=8)).isoformat() + "+08:00"
    for k in ["root_terms", "gap_tags", "weakness_tags", "pain_tags", "evidence_json", "risks", "summary"]:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d
