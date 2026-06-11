from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from . import models
from .api.deps import obj
from .discovery_entries import upsert_candidate_entry


def _content_hash(source_type: str, url: str, title: str, summary: str, raw_excerpt: str) -> str:
    payload = "\n".join(
        [
            (source_type or "").strip().lower(),
            (url or "").strip(),
            (title or "").strip(),
            (summary or "").strip(),
            (raw_excerpt or "").strip()[:1000],
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_evidence_item(
    db: Session,
    source_type: str,
    source_name: str = "",
    url: str = "",
    title: str = "",
    summary: str = "",
    raw_excerpt: str = "",
    raw_json: dict[str, Any] | None = None,
    confidence: float = 0.0,
) -> models.EvidenceItem:
    """Create an objective evidence fact, deduped by content hash."""
    content_hash = _content_hash(source_type, url, title, summary, raw_excerpt)
    row = db.query(models.EvidenceItem).filter_by(content_hash=content_hash).first()
    if row:
        return row
    row = models.EvidenceItem(
        source_type=(source_type or "unknown").strip(),
        source_name=(source_name or "").strip(),
        url=(url or "").strip(),
        title=(title or "").strip(),
        summary=(summary or "").strip(),
        raw_excerpt=(raw_excerpt or "").strip(),
        raw_json=json.dumps(raw_json or {}, ensure_ascii=False),
        confidence=max(0.0, min(1.0, float(confidence or 0.0))),
        content_hash=content_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def link_evidence(
    db: Session,
    evidence_id: int,
    target_type: str,
    target_id: str | int,
    relation_type: str,
    relation_reason: str = "",
    created_by: str = "system",
) -> models.EvidenceLink:
    """Link objective evidence to the object it serves."""
    target_id = str(target_id)
    row = (
        db.query(models.EvidenceLink)
        .filter_by(
            evidence_id=evidence_id,
            target_type=target_type,
            target_id=target_id,
            relation_type=relation_type,
        )
        .first()
    )
    if row:
        if relation_reason:
            row.relation_reason = relation_reason
            db.merge(row)
            db.commit()
            db.refresh(row)
        return row
    row = models.EvidenceLink(
        evidence_id=evidence_id,
        target_type=target_type,
        target_id=target_id,
        relation_type=relation_type,
        relation_reason=relation_reason,
        created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def timeline_for_target(db: Session, target_type: str, target_id: str | int, limit: int = 100) -> list[dict[str, Any]]:
    """Return objective evidence timeline for one service target."""
    rows = (
        db.query(models.EvidenceLink)
        .filter_by(target_type=target_type, target_id=str(target_id))
        .order_by(models.EvidenceLink.created_at.desc())
        .limit(max(1, min(500, limit)))
        .all()
    )
    timeline = []
    for link in rows:
        evidence = db.get(models.EvidenceItem, link.evidence_id)
        timeline.append({"link": obj(link), "evidence": obj(evidence) if evidence else None})
    return timeline


def create_derived_entry_from_evidence(
    db: Session,
    evidence_id: int,
    entry_type: str,
    name: str,
    relation_reason: str,
    source_role: str = "evidence",
) -> models.CandidateEntry:
    """Backflow evidence-derived opportunities into candidate_entries."""
    evidence = db.get(models.EvidenceItem, evidence_id)
    if not evidence:
        raise ValueError("evidence not found")
    entry = upsert_candidate_entry(
        db,
        entry_type=entry_type,
        name=name,
        source=evidence.source_type,
        source_role=source_role,
        source_url=evidence.url,
        raw_context={"derived_from_evidence_id": evidence_id, "reason": relation_reason},
        priority=evidence.confidence * 100,
    )
    link_evidence(db, evidence_id, "candidate_entry", entry.id, "derived_from", relation_reason)
    return entry
