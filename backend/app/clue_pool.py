from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import candidate_scoring, models, services


SOURCE_LABELS = {
    "suggest": "Google Suggest",
    "short_tail_rewrite": "Short Tail Rewrite",
    "root_combo": "Root Combo",
    "sitemap": "Sitemap",
    "domain_web": "Domain Web",
    "alternatives": "Alternative",
    "hot_topic": "Hot Topic",
    "advanced_search": "SERP Search",
    "autopilot": "Autopilot",
}

TREND_SOURCES = {"sitemap", "domain_web", "hot_topic", "hn", "github", "product_hunt", "steam", "arxiv"}
DEMAND_TERMS = {
    "tool",
    "tools",
    "template",
    "calculator",
    "checker",
    "generator",
    "tracker",
    "dashboard",
    "automation",
    "software",
    "workflow",
    "api",
    "integration",
    "alternative",
}


def _json(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _source_label(source: str, method: str = "") -> str:
    if source.startswith("four_find:"):
        return method or source.split(":", 1)[1]
    return SOURCE_LABELS.get(source, method or source or "未知模型")


def _input_ref(evidence: dict[str, Any], row: models.CandidateKeyword) -> dict[str, Any]:
    raw = evidence.get("inputRef") or evidence.get("input_ref")
    if isinstance(raw, dict) and raw.get("value"):
        value = str(raw.get("value") or "")
        kind = str(raw.get("type") or raw.get("kind") or "unknown")
        return {"status": "linked", "type": kind, "value": value, "label": f"{_type_label(kind)} · {value}"}
    for key, kind in (("seed", "keyword"), ("root", "keyword"), ("query", "keyword"), ("topic", "topic"), ("domain", "domain"), ("seed_domain", "domain")):
        if evidence.get(key):
            value = str(evidence.get(key) or "")
            return {"status": "linked", "type": kind, "value": value, "label": f"{_type_label(kind)} · {value}"}
    if row.source_domain:
        return {"status": "linked", "type": "domain", "value": row.source_domain, "label": f"网站 · {row.source_domain}"}
    return {"status": "missing_historical", "type": "unknown", "value": "", "label": "历史记录未保存输入对象"}


def _type_label(kind: str) -> str:
    return {
        "keyword": "搜索词",
        "search_keyword": "搜索词",
        "domain": "网站",
        "url": "页面",
        "topic": "主题",
        "trend_entity": "趋势实体",
    }.get(kind, "对象")


def _clue_type(row: models.CandidateKeyword, evidence: dict[str, Any]) -> str:
    if row.source_domain and not re.search(r"\s", row.keyword or "") and "." in row.keyword:
        return "website"
    if evidence.get("url") and row.source in {"sitemap", "domain_web"}:
        return "page_keyword"
    return "search_keyword"


def _clue_type_label(clue_type: str) -> str:
    return {"search_keyword": "搜索词", "website": "网站", "page_keyword": "页面线索"}.get(clue_type, "线索")


def _scoring_detail(row: models.CandidateKeyword, evidence: dict[str, Any]) -> dict[str, Any]:
    stored = evidence.get("scoring")
    if isinstance(stored, dict) and "candidate_quality_score" in stored:
        return stored
    return candidate_scoring.score_candidate_detail(
        row.keyword,
        source=row.source,
        evidence=evidence,
        base=float(row.score or 0.0),
        seed=str(evidence.get("seed") or evidence.get("root") or evidence.get("query") or ""),
        source_domain=row.source_domain or str(evidence.get("source_domain") or ""),
    )


def _score_parts(row: models.CandidateKeyword, evidence: dict[str, Any], scoring: dict[str, Any]) -> tuple[float, float, float, list[str]]:
    demand = round(float(scoring.get("demand_signal_score") or 0.0), 1)
    trend = round(float(scoring.get("trend_signal_score") or 0.0), 1)
    total = round(demand * 0.65 + trend * 0.35, 1)
    notes = [
        "需求分：来自统一评分中的需求信号，主要看任务/工具意图、商业/行业信号、付费触发和表达质量。",
        "趋势分：来自统一评分中的趋势信号，主要看来源模型是否代表变化、新 URL、首次发现或时间限定搜索。",
        "候选质量分：用于判断这条线索能否进入线索池，不等同于机会价值。",
        f"总评分：需求分 {demand} * 65% + 趋势分 {trend} * 35% = {total}。",
    ]
    for item in scoring.get("breakdown") or []:
        if isinstance(item, dict) and item.get("reason"):
            notes.append(f"{item.get('label') or item.get('dimension')}：{item.get('reason')}")
    return demand, trend, total, notes


def _keyword_match(db: Session, row: models.CandidateKeyword, evidence: dict[str, Any]) -> models.Keyword | None:
    candidates = [evidence.get("imported_query"), evidence.get("canonical_keyword"), row.keyword]
    for value in candidates:
        if not value:
            continue
        found = db.query(models.Keyword).filter(models.Keyword.query == str(value)).first()
        if found:
            return found
    return None


def _opportunity_for_keyword(db: Session, keyword: models.Keyword | None) -> models.OpportunityCard | None:
    if not keyword:
        return None
    return (
        db.query(models.OpportunityCard)
        .filter_by(keyword_id=keyword.id)
        .order_by(models.OpportunityCard.created_at.desc())
        .first()
    )


def _status(row: models.CandidateKeyword, keyword: models.Keyword | None, card: models.OpportunityCard | None, total_score: float) -> tuple[str, str]:
    if row.status == "rejected":
        return "filtered", "已过滤"
    if card:
        return "generated_opportunity", "已生成机会"
    if keyword or row.status == "imported":
        return "keyword_library", "已入关键词库"
    if total_score <= 0:
        return "new", "新发现"
    if total_score < 45:
        return "needs_evidence", "待补证据"
    return "candidate_keyword", "候选关键词"


def _lifecycle_status(status: str) -> tuple[str, str]:
    return {
        "new": ("new", "新发现"),
        "needs_evidence": ("new", "新发现"),
        "candidate_keyword": ("candidate", "候选"),
        "keyword_library": ("in_library", "已入库"),
        "generated_opportunity": ("generated_opportunity", "已生成机会"),
        "filtered": ("filtered", "已过滤"),
        "needs_review": ("new", "新发现"),
    }.get(status, ("new", "新发现"))


def _quality_status(status: str, quality_gate: dict[str, Any]) -> tuple[str, str]:
    if status == "filtered" or quality_gate.get("status") == "blocked":
        return "reject", "拒绝"
    if quality_gate.get("status") == "passed":
        return "pass", "通过"
    return "observe", "观察"


def _processing_status(status: str, quality_status: str) -> tuple[str, str]:
    if status == "filtered" or quality_status == "reject":
        return "needs_review", "需人工处理"
    if status == "needs_evidence" or quality_status == "observe":
        return "needs_evidence", "待补证据"
    return "waiting_auto", "等待自动推进"


def _status_bundle(status: str, quality_gate: dict[str, Any]) -> dict[str, str]:
    lifecycle, lifecycle_label = _lifecycle_status(status)
    quality, quality_label = _quality_status(status, quality_gate)
    processing, processing_label = _processing_status(status, quality)
    return {
        "lifecycle_status": lifecycle,
        "lifecycle_status_label": lifecycle_label,
        "processing_status": processing,
        "processing_status_label": processing_label,
        "quality_status": quality,
        "quality_status_label": quality_label,
    }


def _quality_gate(row: models.CandidateKeyword, evidence: dict[str, Any], status: str, total_score: float) -> dict[str, Any]:
    if status == "filtered":
        return {"status": "blocked", "label": "未通过", "reason": evidence.get("reject_reason") or "已被过滤"}
    if total_score >= 60:
        return {"status": "passed", "label": "通过", "reason": "分数达到候选关键词门槛"}
    return {"status": "needs_evidence", "label": "待补证据", "reason": "分数或证据不足，需要补充线索"}


def _check(status: str, name: str, label: str, reason: str) -> dict[str, str]:
    return {"status": status, "name": name, "label": label, "reason": reason}


def _quality_checks(
    row: models.CandidateKeyword,
    evidence: dict[str, Any],
    status: str,
    demand_score: float,
    trend_score: float,
    total_score: float,
    input_ref: dict[str, Any],
) -> list[dict[str, str]]:
    words = re.findall(r"[a-z0-9]+", (row.keyword or "").lower())
    has_business_intent = bool(set(words) & DEMAND_TERMS)
    is_rejected = status == "filtered" or bool(evidence.get("reject_reason"))
    has_source = input_ref.get("status") == "linked"

    checks = [
        _check(
            "passed" if demand_score >= 70 else "warning" if demand_score >= 45 else "weak",
            "需求明确度",
            "清晰" if demand_score >= 70 else "需观察" if demand_score >= 45 else "偏弱",
            "需求分越高，说明这个词越像用户会主动搜索的具体任务或问题。",
        ),
        _check(
            "passed" if has_business_intent else "warning",
            "商业承接度",
            "可承接" if has_business_intent else "需确认",
            "包含 tool、template、calculator、tracker、automation 等词时，通常更容易形成工具、内容或服务承接。",
        ),
        _check(
            "blocked" if is_rejected else "passed",
            "噪音风险",
            "有风险" if is_rejected else "可接受",
            evidence.get("reject_reason") or "当前没有拒绝原因，噪音风险暂未触发。",
        ),
        _check(
            "passed" if 2 <= len(words) <= 6 else "warning",
            "搜索表达质量",
            "合适" if 2 <= len(words) <= 6 else "需整理",
            "过短容易泛化，过长可能只是一次性表达；2-6 个词通常更适合进入线索池继续观察。",
        ),
        _check(
            "passed" if has_source else "warning",
            "来源可追溯",
            "已关联" if has_source else "历史缺失",
            "已记录输入对象时，可以追溯这条线索来自哪个 seed、网站、页面或主题。",
        ),
        _check(
            "passed" if total_score >= 60 or trend_score >= 50 else "warning",
            "后续可验证性",
            "可推进" if total_score >= 60 or trend_score >= 50 else "需补证",
            "总评分或趋势信号达到一定水平后，才值得继续做 SERP、竞品、社区或页面证据验证。",
        ),
    ]
    return checks


def _assessment(
    row: models.CandidateKeyword,
    status: str,
    quality_gate: dict[str, Any],
    demand_score: float,
    trend_score: float,
    total_score: float,
    input_ref: dict[str, Any],
) -> dict[str, Any]:
    if status == "filtered":
        recommendation = "排除"
    elif total_score >= 80 and demand_score >= 70:
        recommendation = "长期关注"
    elif total_score >= 65:
        recommendation = "短期观察"
    elif quality_gate.get("status") == "needs_evidence":
        recommendation = "补证后再判断"
    else:
        recommendation = "仅保留记录"

    reasons = [
        f"总评分 {total_score}，当前由需求分 {demand_score} 和趋势分 {trend_score} 合成。",
        f"来源模型是 { _source_label(row.source, row.method) }，输入对象是 {input_ref.get('label') or '未记录'}。",
    ]
    if demand_score >= 70:
        reasons.append("需求分较高，说明搜索表达更像明确任务或商业需求。")
    if trend_score >= 50:
        reasons.append("趋势分较高，说明它可能来自新页面、站点变化或早期信号。")

    risks: list[str] = []
    if input_ref.get("status") != "linked":
        risks.append("历史记录缺少输入对象，无法完整追溯这条线索从哪里来。")
    if trend_score < 45:
        risks.append("趋势信号不足，是否值得长期跟踪还需要更多时间或证据。")
    if re.search(r"\b\d{3,}\b", row.keyword or ""):
        risks.append("线索包含数字后缀，需要确认它是产品/年份/型号，还是噪音。")
    if status == "filtered":
        risks.append("线索已经被过滤，继续推进前需要先确认过滤原因是否仍然成立。")

    evidence_gaps: list[str] = []
    if status not in {"keyword_library", "generated_opportunity"}:
        evidence_gaps.append("还没有进入关键词库，需要确认搜索意图、竞争页面和可承接场景。")
    if trend_score < 55:
        evidence_gaps.append("缺少持续变化证据，可以补充 sitemap、changelog、社区或热点信号。")
    if demand_score < 75:
        evidence_gaps.append("需求表达还不够强，可以补充 SERP、Suggest 或相关词证据。")

    next_step = _next_action(status, quality_gate)
    next_step_reason = _next_action_reason(status, quality_gate)
    if recommendation == "长期关注":
        next_step_reason = "这条线索需求明确且总评分较高，应持续观察排名、竞品、社区讨论和商业承接信号。"
    elif recommendation == "短期观察":
        next_step_reason = "这条线索已有一定价值，但还需要更多证据判断是否值得长期跟踪。"
    elif recommendation == "补证后再判断":
        next_step_reason = "当前不足以直接推进，优先补 SERP、竞品、社区或页面变化证据。"

    return {
        "recommendation": recommendation,
        "summary": f"{row.keyword} 当前建议为“{recommendation}”。{next_step_reason}",
        "reasons": reasons,
        "risks": risks or ["暂未发现明显风险，但仍需要结合后续证据持续校验。"],
        "evidence_gaps": evidence_gaps or ["当前已具备基础推进条件，后续重点看证据是否持续增强。"],
        "next_step": next_step,
        "next_step_reason": next_step_reason,
    }


def _candidate_clue(db: Session, row: models.CandidateKeyword) -> dict[str, Any]:
    evidence = _json(row.evidence_json, {})
    if not isinstance(evidence, dict):
        evidence = {}
    scoring = _scoring_detail(row, evidence)
    demand, trend, total, explanation = _score_parts(row, evidence, scoring)
    keyword = _keyword_match(db, row, evidence)
    card = _opportunity_for_keyword(db, keyword)
    status, status_label = _status(row, keyword, card, total)
    clue_type = _clue_type(row, evidence)
    source_run_id = evidence.get("source_run_id") or evidence.get("sourceRunId")
    quality_gate = _quality_gate(row, evidence, status, total)
    status_bundle = _status_bundle(status, quality_gate)
    input_ref = _input_ref(evidence, row)
    quality_checks = _quality_checks(row, evidence, status, demand, trend, total, input_ref)
    assessment = _assessment(row, status, quality_gate, demand, trend, total, input_ref)
    timeline = [
        {"label": "发现线索", "at": _iso(row.created_at), "by": _source_label(row.source, row.method), "reason": "线索模型产生候选对象"},
        {"label": status_label, "at": _iso(row.created_at), "by": "system", "reason": quality_gate["reason"]},
    ]
    return {
        "id": f"candidate_keyword:{row.id}",
        "raw_id": row.id,
        "record_type": "candidate_keyword",
        "clue_type": clue_type,
        "clue_type_label": _clue_type_label(clue_type),
        "value": row.keyword,
        "normalized_value": row.keyword.strip().lower(),
        "status": status,
        "status_label": status_label,
        **status_bundle,
        "source_model": _source_label(row.source, row.method),
        "source_key": row.source,
        "method": row.method,
        "source_run_id": source_run_id,
        "input_ref": input_ref,
        "demand_score": demand,
        "trend_score": trend,
        "total_score": total,
        "quality_gate": quality_gate,
        "quality_checks": quality_checks,
        "assessment": assessment,
        "scoring": scoring,
        "keyword_status": "已入关键词库" if keyword or row.status == "imported" else "未入库",
        "opportunity_status": "已生成机会" if card else "未生成",
        "keyword": None if not keyword else {"id": keyword.id, "query": keyword.query, "status": keyword.status, "score": keyword.score},
        "opportunity": None if not card else {"id": card.id, "title": card.title, "verdict": card.verdict, "score": card.score},
        "evidence": evidence,
        "score_explanation": explanation,
        "next_action": _next_action(status, quality_gate),
        "next_action_reason": _next_action_reason(status, quality_gate),
        "timeline": timeline,
        "created_at": _iso(row.created_at),
        "last_seen_at": _iso(row.created_at),
    }


def _next_action(status: str, quality_gate: dict[str, Any]) -> str:
    if status == "filtered":
        return "可恢复或继续排除"
    if status in {"keyword_library", "generated_opportunity"}:
        return "查看后续分析"
    if quality_gate.get("status") == "needs_evidence":
        return "补证据"
    return "等待自动入库"


def _next_action_reason(status: str, quality_gate: dict[str, Any]) -> str:
    if status == "filtered":
        return "线索处于已过滤状态，下一步只允许人工确认是否恢复或继续排除。"
    if status in {"keyword_library", "generated_opportunity"}:
        return "线索已经进入后续对象，下一步来自当前状态：查看关键词库或机会分析结果。"
    if quality_gate.get("status") == "needs_evidence":
        return "质量门判断证据或分数不足，因此下一步是补证据。"
    return "质量门已经通过，但尚未进入关键词库，因此下一步等待自动入库或人工推送。"


def _entry_clue(row: models.CandidateEntry) -> dict[str, Any]:
    raw = _json(row.raw_context_json, {})
    status = {
        "new": ("new", "新发现"),
        "needs_evidence": ("needs_evidence", "待补证据"),
        "scored": ("candidate_keyword", "候选关键词"),
        "rejected": ("filtered", "已过滤"),
    }.get(row.status, ("needs_review", "需人工处理"))
    trend = round(float(row.trend_score or 0.0), 1)
    demand = round(float(raw.get("demand_score") or raw.get("demandScore") or 0.0), 1) if isinstance(raw, dict) else 0.0
    total = round(max(0.0, min(100.0, demand * 0.65 + trend * 0.35)), 1)
    input_ref = raw.get("inputRef") if isinstance(raw, dict) and isinstance(raw.get("inputRef"), dict) else {"status": "entry_seed", "type": row.entry_type, "value": row.name, "label": f"{_type_label(row.entry_type)} · {row.name}"}
    quality_gate = {"status": "needs_evidence", "label": "待补证据", "reason": "入口线索需要补证、转译或评分"}
    status_bundle = _status_bundle(status[0], quality_gate)
    quality_checks = [
        _check("warning", "需求明确度", "待转译", "入口线索还没有完成关键词转译，需求强度需要后续评分。"),
        _check("warning", "商业承接度", "需确认", "入口线索需要转成更具体的搜索词后，才能判断商业承接。"),
        _check("passed", "噪音风险", "待观察", "当前未记录拒绝原因。"),
        _check("warning", "搜索表达质量", "需整理", "入口线索可能是趋势、页面或对象，需要转成可搜索表达。"),
        _check("passed", "来源可追溯", "已关联", "入口线索本身就是当前输入对象。"),
        _check("warning", "后续可验证性", "需补证", "需要补充 SERP、站点或社区证据后再推进。"),
    ]
    assessment = {
        "recommendation": "补证后再判断",
        "summary": f"{row.name} 还是入口线索，建议先补证、转译或评分，再判断是否进入关键词库。",
        "reasons": ["入口线索代表系统发现的原始机会对象，还不是稳定关键词。", f"趋势分 {trend}，需求分 {demand}。"],
        "risks": ["如果不补充证据，无法判断它是有效需求、趋势实体还是噪音。"],
        "evidence_gaps": ["需要补充搜索意图、来源页面、竞品或社区信号。"],
        "next_step": "补证据" if status[0] == "needs_evidence" else "等待自动推进",
        "next_step_reason": "入口线索还需要补证、转译或评分；当前阶段暂不直接进入关键词库。",
    }
    scoring = {
        "candidate_quality_score": round(max(0.0, min(1.0, total / 100.0)), 3),
        "demand_signal_score": demand,
        "trend_signal_score": trend,
        "noise_risk_score": 0.0,
        "source_confidence_score": 45.0,
        "gate": "watch",
        "reasons": ["entry_needs_translation"],
        "breakdown": [
            {"dimension": "trend", "label": "入口趋势分", "delta": 0.0, "reason": "入口池会先记录趋势强度，表示来源热度、变化信号或人工优先级；它不是最终关键词需求分。"},
            {"dimension": "demand", "label": "需求分待评分", "delta": 0.0, "reason": "入口线索还没有转译成稳定搜索词，需求分需要在转成候选关键词后补齐。"},
        ],
        "formula": "入口线索暂未完成候选词统一评分，需转译后进入候选质量、需求信号、趋势信号拆分。",
    }
    return {
        "id": f"candidate_entry:{row.id}",
        "raw_id": row.id,
        "record_type": "candidate_entry",
        "clue_type": row.entry_type,
        "clue_type_label": _type_label(row.entry_type),
        "value": row.name,
        "normalized_value": row.name.strip().lower(),
        "status": status[0],
        "status_label": status[1],
        **status_bundle,
        "source_model": _source_label(row.source),
        "source_key": row.source,
        "method": row.source_role,
        "source_run_id": raw.get("source_run_id") if isinstance(raw, dict) else None,
        "input_ref": input_ref,
        "demand_score": demand,
        "trend_score": trend,
        "total_score": total,
        "quality_gate": quality_gate,
        "quality_checks": quality_checks,
        "assessment": assessment,
        "scoring": scoring,
        "keyword_status": "未入库",
        "opportunity_status": "未生成",
        "keyword": None,
        "opportunity": None,
        "evidence": raw if isinstance(raw, dict) else {},
        "score_explanation": ["入口趋势分来自入口线索记录，用来表示来源热度、变化信号或人工优先级。", "需求分待评分：入口线索需要先转译成稳定搜索词，再补齐需求信号。"],
        "next_action": "补证据" if status[0] == "needs_evidence" else "等待自动推进",
        "next_action_reason": "入口线索还需要补证、转译或评分；当前阶段暂不直接进入关键词库。",
        "timeline": [{"label": "发现线索", "at": _iso(row.created_at), "by": _source_label(row.source), "reason": "入口池记录"}],
        "created_at": _iso(row.created_at),
        "last_seen_at": _iso(row.updated_at or row.created_at),
    }


def list_clues(
    db: Session,
    limit: int = 100,
    status: str = "",
    clue_type: str = "",
    source: str = "",
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    candidate_rows = (
        db.query(models.CandidateKeyword)
        .order_by(models.CandidateKeyword.created_at.desc())
        .limit(max(1, min(500, limit)))
        .all()
    )
    items.extend(_candidate_clue(db, row) for row in candidate_rows)

    entry_rows = (
        db.query(models.CandidateEntry)
        .order_by(models.CandidateEntry.priority.desc(), models.CandidateEntry.created_at.desc())
        .limit(max(1, min(500, limit)))
        .all()
    )
    items.extend(_entry_clue(row) for row in entry_rows)

    if status:
        items = [item for item in items if item["status"] == status]
    if clue_type:
        items = [item for item in items if item["clue_type"] == clue_type]
    if source:
        items = [item for item in items if item["source_key"] == source]
    items.sort(key=lambda item: (item.get("total_score") or 0, item.get("created_at") or ""), reverse=True)
    items = items[: max(1, min(500, limit))]
    totals: dict[str, int] = {}
    for item in items:
        totals[item["status"]] = totals.get(item["status"], 0) + 1
    return {"items": items, "totals": totals, "count": len(items)}


def _find_clue(db: Session, clue_id: str) -> dict[str, Any] | None:
    if clue_id.startswith("candidate_keyword:"):
        raw_id = clue_id.split(":", 1)[1]
        if raw_id.isdigit():
            row = db.query(models.CandidateKeyword).filter_by(id=int(raw_id)).first()
            return _candidate_clue(db, row) if row else None
    if clue_id.startswith("candidate_entry:"):
        raw_id = clue_id.split(":", 1)[1]
        if raw_id.isdigit():
            row = db.query(models.CandidateEntry).filter_by(id=int(raw_id)).first()
            return _entry_clue(row) if row else None
    return None


def _compact_clue_for_llm(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "线索": item.get("value"),
        "生命周期状态": item.get("lifecycle_status_label"),
        "处理状态": item.get("processing_status_label"),
        "质量状态": item.get("quality_status_label"),
        "来源模型": item.get("source_model"),
        "输入对象": (item.get("input_ref") or {}).get("label"),
        "需求分": item.get("demand_score"),
        "趋势分": item.get("trend_score"),
        "总评分": item.get("total_score"),
        "候选质量分": (item.get("scoring") or {}).get("candidate_quality_score"),
        "质量门": item.get("quality_gate"),
        "规则研判": item.get("assessment"),
        "客观检查": item.get("quality_checks"),
        "关键词库状态": item.get("keyword_status"),
        "机会状态": item.get("opportunity_status"),
        "产生时间": item.get("created_at"),
    }


def _normalize_llm_analysis(obj: dict[str, Any]) -> dict[str, Any]:
    def strings(key: str) -> list[str]:
        value = obj.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return {
        "verdict": str(obj.get("verdict") or obj.get("recommendation") or "需人工复核"),
        "summary": str(obj.get("summary") or ""),
        "long_term_fit": str(obj.get("long_term_fit") or obj.get("fit") or "unknown"),
        "reasoning": strings("reasoning") or strings("reasons"),
        "risks": strings("risks"),
        "evidence_to_collect": strings("evidence_to_collect") or strings("evidence_gaps"),
        "next_actions": strings("next_actions"),
        "provider": obj.get("_llm_provider"),
    }


def llm_analysis_for_clue(db: Session, clue_id: str) -> dict[str, Any]:
    item = _find_clue(db, clue_id)
    if not item:
        return {"ok": False, "status": "not_found", "source": "none", "analysis": None, "message": "线索不存在"}

    system = (
        "你是 Demand Hunter 的机会线索分析助手。只返回 JSON。"
        "不要编造外部事实，只基于输入中的线索、来源、分数、质量门和客观检查做研判。"
        "JSON 字段必须包含 verdict, summary, long_term_fit, reasoning, risks, evidence_to_collect, next_actions。"
    )
    user = json.dumps(
        {
            "task": "判断这条机会线索是否值得长期关注，并说明还需要补哪些证据。",
            "clue": _compact_clue_for_llm(item),
        },
        ensure_ascii=False,
    )
    obj = services._llm_json(db, system, user, temperature=0.15)
    if not obj:
        return {
            "ok": False,
            "status": "llm_unavailable",
            "source": "none",
            "analysis": None,
            "message": "LLM 未配置或未返回有效 JSON，当前没有生成 LLM 研判。",
        }
    return {"ok": True, "status": "ok", "source": "llm", "analysis": _normalize_llm_analysis(obj)}
