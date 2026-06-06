from __future__ import annotations
import json
from typing import Any


def obj(row: Any) -> dict:
    """Serialize SQLAlchemy row and parse JSON-encoded columns used by the API."""
    d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    for k in ["root_terms", "gap_tags", "weakness_tags", "pain_tags", "evidence_json", "risks", "summary"]:
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d
