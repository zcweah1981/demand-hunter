from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import models

TREND_ENTRY_TYPES = {"trend_entity", "github_repo", "game", "tool_name", "feature", "platform_update"}


def _clean_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def upsert_candidate_entry(
    db: Session,
    entry_type: str,
    name: str,
    source: str = "",
    source_role: str = "",
    source_url: str = "",
    raw_context: dict[str, Any] | None = None,
    priority: float = 0.0,
) -> models.CandidateEntry:
    """Create or update a candidate entry without promoting it to keywords."""
    entry_type = _clean_text(entry_type).lower()
    name = _clean_text(name)
    source = _clean_text(source)
    source_url = _clean_text(source_url)
    if not entry_type or not name:
        raise ValueError("entry_type and name are required")
    if not source_role:
        source_role = "trend" if entry_type in TREND_ENTRY_TYPES else "demand"

    row = (
        db.query(models.CandidateEntry)
        .filter_by(entry_type=entry_type, name=name, source=source, source_url=source_url)
        .first()
    )
    payload = json.dumps(raw_context or {}, ensure_ascii=False)
    if not row:
        row = models.CandidateEntry(
            entry_type=entry_type,
            name=name,
            source=source,
            source_role=source_role,
            source_url=source_url,
            raw_context_json=payload,
            priority=priority,
            status="new",
        )
        db.add(row)
    else:
        row.source_role = source_role or row.source_role
        row.raw_context_json = payload or row.raw_context_json
        row.priority = max(row.priority or 0.0, priority)
        row.updated_at = datetime.utcnow()
        db.merge(row)
    db.commit()
    db.refresh(row)
    return row


def route_entry_next_action(entry: models.CandidateEntry) -> str:
    if entry.entry_type == "search_keyword":
        return "score_demand_keyword"
    if entry.entry_type in TREND_ENTRY_TYPES:
        return "score_trend_entity"
    if entry.entry_type == "domain":
        return "create_evidence_task"
    return "needs_review"
