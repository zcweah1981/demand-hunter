from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from . import models
from .api.deps import obj


@dataclass(frozen=True)
class EvidenceModelDef:
    id: str
    name: str
    group: str
    purpose: str
    loop: str
    sources: tuple[str, ...]
    methods: tuple[str, ...] = ()


MODEL_CATALOG: tuple[EvidenceModelDef, ...] = (
    EvidenceModelDef(
        id="keyword_to_keyword",
        name="词找词",
        group="四找模型",
        purpose="从一个搜索词继续扩展更多用户表达。",
        loop="种子词 -> 扩展候选词 -> 补证据 -> 进入候选关键词或关键词库",
        sources=("suggest", "google_suggest", "duckduckgo", "short_tail_rewrite", "related", "paa"),
        methods=("词找词",),
    ),
    EvidenceModelDef(
        id="keyword_to_site",
        name="词找站",
        group="四找模型",
        purpose="用搜索词找到正在承接需求的网站、竞品和内容占位。",
        loop="搜索词 -> SERP/站点 -> 竞品与页面证据 -> 机会验证",
        sources=("advanced_search", "serp", "domain_search"),
        methods=("词找站", "搜索结果挖掘"),
    ),
    EvidenceModelDef(
        id="site_to_keyword",
        name="站找词",
        group="四找模型",
        purpose="从竞品站、sitemap、页面标题和内容中反查更多需求词。",
        loop="站点 -> 页面变化/内容证据 -> 新入口或候选关键词",
        sources=("sitemap", "domain_web", "sitemap_monitor", "web_content"),
        methods=("站找词", "页面标题/Meta 找词"),
    ),
    EvidenceModelDef(
        id="site_to_site",
        name="站找站",
        group="四找模型",
        purpose="从竞品和替代品扩展相邻站点与赛道。",
        loop="竞品站 -> 替代/对比证据 -> 新站点入口 -> 再进入站找词",
        sources=("alternatives", "alternative", "competitor", "similar_site"),
        methods=("站找站",),
    ),
    EvidenceModelDef(
        id="trend_capture",
        name="新趋势捕捉",
        group="趋势模型",
        purpose="发现新工具、新项目、新游戏、新模型和平台变化。",
        loop="早期信号 -> 趋势入口 -> 趋势评分 -> 转译为候选关键词",
        sources=("source_radar", "hot_topic", "hn_algolia", "arxiv", "github", "product_hunt", "steam"),
        methods=("热点词/新鲜度找词", "信息溯源"),
    ),
    EvidenceModelDef(
        id="change_monitor",
        name="变化监控",
        group="监控模型",
        purpose="持续观察竞品、定价、changelog、社区讨论和页面变化。",
        loop="监控对象 -> 新证据 -> 触发重评分/补证/新入口回流",
        sources=("pricing_page", "changelog", "community", "docs_page", "watch_target", "review", "social"),
        methods=("变化监控",),
    ),
)


def _source_set(item: EvidenceModelDef) -> set[str]:
    return {s.lower() for s in item.sources}


def _method_match(value: str, item: EvidenceModelDef) -> bool:
    value = value or ""
    return any(m and m in value for m in item.methods)


def source_to_model_id(source: str = "", method: str = "") -> str:
    source_key = (source or "").strip().lower()
    for item in MODEL_CATALOG:
        if source_key in _source_set(item) or _method_match(method, item):
            return item.id
    return "unmapped"


def model_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "group": item.group,
            "purpose": item.purpose,
            "loop": item.loop,
            "sources": list(item.sources),
            "methods": list(item.methods),
        }
        for item in MODEL_CATALOG
    ]


def _empty_stats() -> dict[str, int]:
    return {
        "runs": 0,
        "evidence": 0,
        "entries": 0,
        "candidate_keywords": 0,
        "keywords": 0,
        "cards": 0,
        "errors": 0,
    }


def _blank_model(item: EvidenceModelDef) -> dict[str, Any]:
    return {
        **model_catalog()[[x.id for x in MODEL_CATALOG].index(item.id)],
        "stats": _empty_stats(),
        "recent_evidence": [],
        "recent_entries": [],
        "recent_keywords": [],
        "recent_runs": [],
    }


def _models_by_id() -> dict[str, dict[str, Any]]:
    return {item.id: _blank_model(item) for item in MODEL_CATALOG}


def model_overview(db: Session) -> dict[str, Any]:
    models_by_id = _models_by_id()

    for row in db.query(models.SourceRun).order_by(models.SourceRun.started_at.desc()).limit(500).all():
        mid = source_to_model_id(row.source, row.run_kind)
        bucket = models_by_id.get(mid)
        if not bucket:
            continue
        bucket["stats"]["runs"] += 1
        bucket["stats"]["entries"] += int(row.candidates_created or 0)
        bucket["stats"]["evidence"] += int(row.evidence_created or 0)
        bucket["stats"]["keywords"] += int(row.keywords_promoted or 0)
        bucket["stats"]["cards"] += int(row.cards_generated or 0)
        bucket["stats"]["errors"] += 1 if (row.errors or "[]") not in ("", "[]") else 0
        if len(bucket["recent_runs"]) < 5:
            bucket["recent_runs"].append(obj(row))

    for row in db.query(models.EvidenceItem).order_by(models.EvidenceItem.captured_at.desc()).limit(800).all():
        mid = source_to_model_id(row.source_type, row.source_name)
        bucket = models_by_id.get(mid)
        if not bucket:
            continue
        bucket["stats"]["evidence"] += 1
        if len(bucket["recent_evidence"]) < 5:
            bucket["recent_evidence"].append(obj(row))

    for row in db.query(models.CandidateEntry).order_by(models.CandidateEntry.created_at.desc()).limit(800).all():
        mid = source_to_model_id(row.source, row.source_role)
        bucket = models_by_id.get(mid)
        if not bucket:
            continue
        bucket["stats"]["entries"] += 1
        if len(bucket["recent_entries"]) < 5:
            bucket["recent_entries"].append(obj(row))

    for row in db.query(models.CandidateKeyword).order_by(models.CandidateKeyword.created_at.desc()).limit(1200).all():
        mid = source_to_model_id(row.source, row.method)
        bucket = models_by_id.get(mid)
        if not bucket:
            continue
        bucket["stats"]["candidate_keywords"] += 1
        if len(bucket["recent_keywords"]) < 5:
            bucket["recent_keywords"].append(obj(row))

    for keyword in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(1200).all():
        mid = source_to_model_id(keyword.source, keyword.intent)
        bucket = models_by_id.get(mid)
        if not bucket:
            continue
        bucket["stats"]["keywords"] += 1
        bucket["stats"]["cards"] += db.query(models.OpportunityCard).filter_by(keyword_id=keyword.id).count()

    result = list(models_by_id.values())
    totals = _empty_stats()
    for item in result:
        for key, value in item["stats"].items():
            totals[key] += int(value or 0)
    return {"items": result, "totals": totals}


def model_detail(db: Session, model_id: str) -> dict[str, Any] | None:
    overview = model_overview(db)
    base = next((item for item in overview["items"] if item["id"] == model_id), None)
    if not base:
        return None

    source_keys = set(base["sources"])
    method_keys = set(base["methods"])
    evidence = [
        obj(row)
        for row in db.query(models.EvidenceItem).order_by(models.EvidenceItem.captured_at.desc()).limit(1200).all()
        if source_to_model_id(row.source_type, row.source_name) == model_id
    ][:80]
    entries = [
        obj(row)
        for row in db.query(models.CandidateEntry).order_by(models.CandidateEntry.created_at.desc()).limit(1200).all()
        if source_to_model_id(row.source, row.source_role) == model_id
    ][:80]
    candidates = [
        obj(row)
        for row in db.query(models.CandidateKeyword).order_by(models.CandidateKeyword.created_at.desc()).limit(1500).all()
        if source_to_model_id(row.source, row.method) == model_id
    ][:80]
    runs = [
        obj(row)
        for row in db.query(models.SourceRun).order_by(models.SourceRun.started_at.desc()).limit(500).all()
        if source_to_model_id(row.source, row.run_kind) == model_id
    ][:50]

    return {
        **base,
        "source_keys": list(source_keys),
        "method_keys": list(method_keys),
        "evidence": evidence,
        "entries": entries,
        "candidate_keywords": candidates,
        "runs": runs,
    }
