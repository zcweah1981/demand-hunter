from __future__ import annotations

import re
from typing import Any

TOOL_TERMS = {
    "calculator",
    "template",
    "checker",
    "tracker",
    "planner",
    "generator",
    "database",
    "monitor",
    "dashboard",
    "automation",
    "integration",
    "api",
}

COMMERCIAL_TERMS = {
    "shopify",
    "tax",
    "invoice",
    "pricing",
    "cost",
    "compliance",
    "quickbooks",
    "stripe",
    "paypal",
    "b2b",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t}


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def score_demand_keyword(keyword: str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Score a mature search-demand keyword for the keyword quality gate."""
    terms = _tokens(keyword)
    evidence = evidence or []
    demand_clarity = 20 if len(terms) >= 3 else 12 if len(terms) == 2 else 6
    commercial_intent = 20 if terms & COMMERCIAL_TERMS else 10
    mvp_fit = 20 if terms & TOOL_TERMS else 8
    evidence_boost = min(20, len(evidence) * 4)
    serp_gap = 10 + evidence_boost
    weak_competition = 10 + min(10, sum(1 for e in evidence if str(e.get("relation_type", "")).startswith("weak")))
    monetization = 18 if terms & (TOOL_TERMS | COMMERCIAL_TERMS) else 8
    breakdown = {
        "demand_clarity": _clamp_score(demand_clarity),
        "commercial_intent": _clamp_score(commercial_intent),
        "serp_gap": _clamp_score(serp_gap),
        "weak_competition": _clamp_score(weak_competition),
        "mvp_fit": _clamp_score(mvp_fit),
        "monetization": _clamp_score(monetization),
    }
    score = _clamp_score(sum(breakdown.values()) / 120 * 100)
    if score >= 70:
        quality_gate = "pass"
    elif score >= 45:
        quality_gate = "watch"
    else:
        quality_gate = "reject"
    return {"score": score, "breakdown": breakdown, "quality_gate": quality_gate}


def score_trend_entity(name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score a trend entity. Trend entities must be translated before keywords."""
    context = context or {}
    raw_heat = float(context.get("heat", 0) or 0)
    raw_problem = float(context.get("problem_density", 0) or 0)
    raw_gap = float(context.get("ecosystem_gap", 0) or 0)
    terms = _tokens(name)
    toolability = 20 if terms & TOOL_TERMS else 12
    translation_potential = 18 if len(terms) <= 4 else 12
    breakdown = {
        "growth": _clamp_score(raw_heat or 12),
        "problem_density": _clamp_score(raw_problem or 10),
        "ecosystem_gap": _clamp_score(raw_gap or 10),
        "toolability": _clamp_score(toolability),
        "translation_potential": _clamp_score(translation_potential),
    }
    score = _clamp_score(sum(breakdown.values()))
    if score >= 65:
        next_action = "translate"
    elif score >= 40:
        next_action = "watch"
    else:
        next_action = "reject"
    return {"score": score, "breakdown": breakdown, "next_action": next_action}
