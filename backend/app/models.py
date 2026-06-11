from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class DiscoveryExpansion(Base):
    """词找词 expansion:从一个 seed keyword 扩展出更多搜索词"""
    __tablename__ = "discovery_expansions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed_keyword: Mapped[str] = mapped_column(String(260), index=True)
    expanded_keyword: Mapped[str] = mapped_column(String(260))
    expansion_type: Mapped[str] = mapped_column(String(60))  # suggest, related, modifier, paa
    source_domain: Mapped[str] = mapped_column(String(255), default="")  # which domain we found it from
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="new")  # new, imported, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CompetitorKeyword(Base):
    """站找词:从竞品域名反查到的关键词"""
    __tablename__ = "competitor_keywords"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_domain: Mapped[str] = mapped_column(String(255), index=True)
    discovered_keyword: Mapped[str] = mapped_column(String(260))
    source: Mapped[str] = mapped_column(String(80))  # sitemap, title, url_path, site_search
    source_url: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CompetitorSite(Base):
    """站找站:从一个竞品找到的相似站"""
    __tablename__ = "competitor_sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed_domain: Mapped[str] = mapped_column(String(255), index=True)
    similar_domain: Mapped[str] = mapped_column(String(255))
    discovery_method: Mapped[str] = mapped_column(String(80))  # alternative_to, directory, reddit
    source_url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Root(Base):
    __tablename__ = "roots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), default="tool")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("query", name="uq_keywords_query"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query: Mapped[str] = mapped_column(String(260), index=True)
    source: Mapped[str] = mapped_column(String(80), default="manual")
    root_terms: Mapped[str] = mapped_column(Text, default="[]")
    intent: Mapped[str] = mapped_column(String(80), default="unknown")
    status: Mapped[str] = mapped_column(String(40), default="new")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    serp_results: Mapped[list[SerpResult]] = relationship(back_populates="keyword", cascade="all, delete-orphan")
    cards: Mapped[list[OpportunityCard]] = relationship(back_populates="keyword", cascade="all, delete-orphan")

class SerpResult(Base):
    __tablename__ = "serp_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(255), default="")
    gap_tags: Mapped[str] = mapped_column(Text, default="[]")
    weakness_score: Mapped[float] = mapped_column(Float, default=0.0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    keyword: Mapped[Keyword] = relationship(back_populates="serp_results")

class CompetitorPage(Base):
    __tablename__ = "competitor_pages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(255), default="")
    title: Mapped[str] = mapped_column(Text, default="")
    weakness_tags: Mapped[str] = mapped_column(Text, default="[]")
    content_excerpt: Mapped[str] = mapped_column(Text, default="")
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SocialEvidence(Base):
    __tablename__ = "social_evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    platform: Mapped[str] = mapped_column(String(60), default="web")
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    pain_tags: Mapped[str] = mapped_column(Text, default="[]")
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OpportunityCard(Base):
    __tablename__ = "opportunity_cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("keywords.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(40), default="Watch")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    demand_score: Mapped[float] = mapped_column(Float, default=0.0)
    serp_gap_score: Mapped[float] = mapped_column(Float, default=0.0)
    competitor_weakness_score: Mapped[float] = mapped_column(Float, default=0.0)
    mvp_score: Mapped[float] = mapped_column(Float, default=0.0)
    monetization_score: Mapped[float] = mapped_column(Float, default=0.0)
    monetization_type: Mapped[str] = mapped_column(String(80), default="unknown")
    mvp_plan: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    risks: Mapped[str] = mapped_column(Text, default="[]")
    feedback_label: Mapped[str] = mapped_column(String(40), default="")
    feedback_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    keyword: Mapped[Keyword] = relationship(back_populates="cards")

class RunHistory(Base):
    __tablename__ = "run_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(60), default="daily")
    status: Mapped[str] = mapped_column(String(40), default="running")
    summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class CandidateKeyword(Base):
    """Unified collector candidate pool before Four-Find / SEO validation."""
    __tablename__ = "candidate_keywords"
    __table_args__ = (UniqueConstraint("keyword", "source", "source_url", name="uq_candidate_keyword_source"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(260), index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)  # sitemap, suggest, related, hn, arxiv, etc.
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_domain: Mapped[str] = mapped_column(String(255), default="")
    method: Mapped[str] = mapped_column(String(80), default="")  # 词找词/站找词/信息溯源
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="new")  # new, imported, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CandidateEntry(Base):
    """Unified entry pool before keyword translation and evidence validation."""
    __tablename__ = "candidate_entries"
    __table_args__ = (
        UniqueConstraint("entry_type", "name", "source", "source_url", name="uq_candidate_entry_source"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    source: Mapped[str] = mapped_column(String(100), index=True, default="")
    source_role: Mapped[str] = mapped_column(String(40), index=True, default="demand")
    source_url: Mapped[str] = mapped_column(Text, default="")
    raw_context_json: Mapped[str] = mapped_column(Text, default="{}")
    trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    maturity_type: Mapped[str] = mapped_column(String(40), default="unknown")
    status: Mapped[str] = mapped_column(String(40), index=True, default="new")
    priority: Mapped[float] = mapped_column(Float, default=0.0)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvidenceItem(Base):
    """Objective evidence fact. Interpretation lives in links and events."""
    __tablename__ = "evidence_items"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_evidence_content_hash"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    raw_excerpt: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    content_hash: Mapped[str] = mapped_column(String(120), index=True)
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvidenceLink(Base):
    """Service relation showing which object an objective evidence item serves."""
    __tablename__ = "evidence_links"
    __table_args__ = (
        UniqueConstraint("evidence_id", "target_type", "target_id", "relation_type", name="uq_evidence_link_target"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence_items.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True)
    target_id: Mapped[str] = mapped_column(String(80), index=True)
    relation_type: Mapped[str] = mapped_column(String(80), index=True)
    relation_reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(60), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceRun(Base):
    """Unified source execution record for ROI and automation traceability."""
    __tablename__ = "source_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_role: Mapped[str] = mapped_column(String(40), index=True, default="demand")
    run_kind: Mapped[str] = mapped_column(String(80), index=True, default="manual")
    status: Mapped[str] = mapped_column(String(40), index=True, default="ok")
    inputs_json: Mapped[str] = mapped_column(Text, default="{}")
    outputs_json: Mapped[str] = mapped_column(Text, default="{}")
    candidates_created: Mapped[int] = mapped_column(Integer, default=0)
    evidence_created: Mapped[int] = mapped_column(Integer, default=0)
    keywords_promoted: Mapped[int] = mapped_column(Integer, default=0)
    cards_generated: Mapped[int] = mapped_column(Integer, default=0)
    actions_created: Mapped[int] = mapped_column(Integer, default=0)
    rejects_created: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str] = mapped_column(Text, default="[]")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WatchTarget(Base):
    """Object monitored by the evidence system through the unified cycle."""
    __tablename__ = "watch_targets"
    __table_args__ = (UniqueConstraint("target_type", "target_key", "source_url", name="uq_watch_target"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True)
    target_key: Mapped[str] = mapped_column(String(300), index=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_name: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), index=True, default="active")
    priority: Mapped[float] = mapped_column(Float, default=0.0)
    cadence_hint: Mapped[str] = mapped_column(String(40), default="cycle")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    raw_context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActionRequest(Base):
    """User or system requested action with risk-aware execution."""
    __tablename__ = "action_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_type: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True)
    target_id: Mapped[str] = mapped_column(String(80), index=True)
    risk_level: Mapped[str] = mapped_column(String(20), index=True, default="low")
    status: Mapped[str] = mapped_column(String(40), index=True, default="pending")
    requested_by: Mapped[str] = mapped_column(String(60), default="user")
    reason: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ActionEvent(Base):
    """Audit event emitted when an action request is executed or rejected."""
    __tablename__ = "action_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("action_requests.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True, default="")
    target_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KeywordWeightEvent(Base):
    """Keyword weight timeline derived from objective evidence and gates."""
    __tablename__ = "keyword_weight_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword_ref_type: Mapped[str] = mapped_column(String(40), index=True, default="candidate_keyword")
    keyword_ref_id: Mapped[str] = mapped_column(String(80), index=True)
    previous_weight: Mapped[float] = mapped_column(Float, default=0.0)
    new_weight: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_link_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OpportunityScoreEvent(Base):
    """Opportunity score timeline; evidence remains objective and separate."""
    __tablename__ = "opportunity_score_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_card_id: Mapped[int] = mapped_column(Integer, index=True)
    previous_score: Mapped[float] = mapped_column(Float, default=0.0)
    new_score: Mapped[float] = mapped_column(Float, default=0.0)
    previous_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    new_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence_link_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CollectorTarget(Base):
    """Automatic collector target pool.

    Targets are generated from Action/Watch cards, SERP competitor domains,
    feedback, and later trend sources. They replace manual-only collector seeds.
    """
    __tablename__ = "collector_targets"
    __table_args__ = (UniqueConstraint("target_type", "value", "source_type", "source_id", name="uq_collector_target_source"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(40), index=True)  # keyword, domain
    value: Mapped[str] = mapped_column(String(260), index=True)
    source_type: Mapped[str] = mapped_column(String(60), default="opportunity_card")
    source_id: Mapped[str] = mapped_column(String(80), default="")
    topic: Mapped[str] = mapped_column(String(160), default="")
    priority: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="active")  # active, cooldown, rejected, exhausted
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    reject_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SitemapSeenUrl(Base):
    """Track sitemap URL diff so sitemap watcher reports only newly seen pages."""
    __tablename__ = "sitemap_seen_urls"
    __table_args__ = (UniqueConstraint("url", name="uq_sitemap_seen_url"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(255), index=True, default="")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    seen_count: Mapped[int] = mapped_column(Integer, default=1)
    last_keyword: Mapped[str] = mapped_column(String(260), default="")

class MvpProject(Base):
    """Post-Adopted opportunity validation and MVP progress project."""
    __tablename__ = "mvp_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_group_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    canonical_keyword: Mapped[str] = mapped_column(String(260), index=True)
    representative_card_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(40), default="needs_prd")
    prd_path: Mapped[str] = mapped_column(Text, default="")
    prd_version: Mapped[int] = mapped_column(Integer, default=0)
    prd_content: Mapped[str] = mapped_column(Text, default="")
    feasibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(40), default="unknown")
    next_action: Mapped[str] = mapped_column(Text, default="上传或填写 PRD 后开始验证。")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_validation_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_validation_schedule: Mapped[str] = mapped_column(String(20), default="weekly")
    auto_validation_hour: Mapped[int] = mapped_column(Integer, default=9)
    auto_validation_minute: Mapped[int] = mapped_column(Integer, default=0)
    auto_validation_weekday: Mapped[int] = mapped_column(Integer, default=1)
    next_auto_validation_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_auto_validation_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class MvpValidationRun(Base):
    __tablename__ = "mvp_validation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(60), default="full_validation")
    status: Mapped[str] = mapped_column(String(40), default="running")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class TrackedCompetitor(Base):
    __tablename__ = "tracked_competitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    pricing_url: Mapped[str] = mapped_column(Text, default="")
    sitemap_url: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="tracking")
    notes: Mapped[str] = mapped_column(Text, default="")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CompetitorSnapshot(Base):
    __tablename__ = "competitor_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(Integer, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(60), default="page")
    url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(120), default="")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProgressHypothesis(Base):
    __tablename__ = "progress_hypotheses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="unverified")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProgressEvidenceTask(Base):
    __tablename__ = "progress_evidence_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    hypothesis_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    query: Mapped[str] = mapped_column(String(300), index=True)
    task_type: Mapped[str] = mapped_column(String(60), default="web_search")
    status: Mapped[str] = mapped_column(String(40), default="pending")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    result_summary: Mapped[str] = mapped_column(Text, default="")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProgressEvidenceItem(Base):
    __tablename__ = "progress_evidence_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    hypothesis_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    task_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    title: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    source_domain: Mapped[str] = mapped_column(String(255), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    effect: Mapped[str] = mapped_column(String(40), default="neutral")
    reason: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MvpStrategyRecommendation(Base):
    __tablename__ = "mvp_strategy_recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(60), default="strategy")
    title: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
