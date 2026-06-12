from __future__ import annotations

import re
from typing import Any


TOOL_INTENT_TERMS = {
    "calculator",
    "generator",
    "template",
    "checker",
    "converter",
    "tracker",
    "dashboard",
    "analyzer",
    "builder",
    "creator",
    "planner",
    "estimator",
    "form",
    "spreadsheet",
    "invoice",
    "policy",
    "report",
    "monitor",
    "automation",
    "integration",
    "api",
    "alternative",
    "software",
    "tool",
    "workflow",
    "checklist",
}

COMMERCIAL_TERMS = {
    "pricing",
    "price",
    "cost",
    "fee",
    "invoice",
    "tax",
    "compliance",
    "shopify",
    "woocommerce",
    "quickbooks",
    "hubspot",
    "salesforce",
    "stripe",
    "paypal",
    "b2b",
    "business",
    "agency",
    "client",
    "contractor",
    "clinic",
    "rental",
    "vendor",
    "employee",
    "audit",
    "permit",
    "renewal",
    "training",
    "payment",
}

GOOD_MODIFIERS = {
    "clinic",
    "dental",
    "salon",
    "doctor",
    "patient",
    "client",
    "contractor",
    "rental",
    "reminder",
    "cancellation",
    "reschedule",
    "intake",
    "form",
    "sms",
    "calendar",
    "workflow",
    "dashboard",
    "tracker",
    "checklist",
    "calculator",
    "software",
    "management",
    "deadline",
    "compliance",
    "invoice",
    "booking",
    "schedule",
    "scheduling",
    "policy",
    "report",
    "audit",
    "vendor",
    "employee",
    "training",
    "risk",
    "inspection",
    "renewal",
    "permit",
    "late",
    "fee",
    "payment",
    "tax",
    "estimate",
    "overdue",
    "receipt",
    "penalty",
    "cost",
    "ai",
}

BAD_KEYWORD_TERMS = {
    "login",
    "sign in",
    "signup",
    "get started",
    "contact",
    "support",
    "pricing",
    "city",
    "county",
    "california",
    "near me",
    "home",
    "official",
    "portal",
    "capterra",
    "g2",
    "trustradius",
    "spectrum",
    "facebook",
    "linkedin",
    "youtube",
    "dmv",
    "gov",
}

BAD_SINGLE_MODIFIERS = {"for", "and", "with", "from", "your", "their", "this", "that", "login", "city", "home", "page", "about", "contact", "support", "license", "portal", "map", "started"}

TITLE_RESIDUE_PATTERNS = (
    r"^[a-z0-9][a-z0-9 ._-]{1,24}:\s+",
    r"\bwhich\s+.+\bbest\b",
    r"\b(best|top)\s+.+\bfor\s+your\b",
    r"\bfor\s+your\s+(small\s+)?business\b",
    r"\?$",
    r"\b(best|top)\b.+\b(plugin|plugins|extension|extensions|software|apps?)\b",
    r"\b(plugin|plugins|extension|extensions)\b.+\b(compared|comparison|review|reviews)\b",
    r"\b(compared|comparison|review|reviews)\b",
)

EARLY_SOURCE_BONUS = {
    "sitemap": 0.16,
    "advanced_search": 0.12,
    "hn_algolia": 0.10,
    "hot_topic": 0.10,
    "arxiv": 0.08,
    "google_suggest": 0.06,
    "suggest": 0.06,
    "duckduckgo": 0.05,
    "domain_web": 0.10,
    "alternatives": 0.08,
}

TREND_SOURCES = {"sitemap", "domain_web", "hot_topic", "hn_algolia", "github", "product_hunt", "steam", "arxiv"}
WEAK_SOURCE_DOMAINS = ("capterra.com", "g2.com", "spectrum.com", "facebook.com", "linkedin.com")


def _normalize_keyword(keyword: str) -> str:
    value = re.sub(r"[^a-z0-9\s-]", " ", (keyword or "").lower())
    value = value.replace("-", " ")
    return re.sub(r"\s+", " ", value).strip()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _add_breakdown(items: list[dict[str, Any]], dimension: str, label: str, delta: float, reason: str) -> None:
    items.append({"dimension": dimension, "label": label, "delta": round(delta, 3), "reason": reason})


def score_candidate_detail(
    keyword: str,
    source: str = "",
    evidence: dict[str, Any] | None = None,
    base: float = 0.0,
    seed: str = "",
    source_domain: str = "",
) -> dict[str, Any]:
    evidence = evidence or {}
    source = source or ""
    kw = _normalize_keyword(keyword)
    if not kw:
        return {
            "candidate_quality_score": 0.0,
            "demand_signal_score": 0.0,
            "trend_signal_score": 0.0,
            "noise_risk_score": 100.0,
            "source_confidence_score": 0.0,
            "gate": "reject",
            "reasons": ["empty_or_too_short"],
            "breakdown": [],
            "formula": "候选质量分 = 文本质量 + 商业/任务意图 + 来源可信 + 新鲜度 - 噪音风险",
        }

    terms = kw.split()
    term_set = set(terms)
    seed_l = _normalize_keyword(seed or str(evidence.get("seed") or evidence.get("root") or ""))
    seed_terms = set(seed_l.split())
    added_words = term_set - seed_terms
    breakdown: list[dict[str, Any]] = []
    reasons: list[str] = []

    quality = max(base, 0.55 if source == "four_find" else 0.35)
    demand = 35.0
    trend = 20.0
    noise = 0.0
    source_confidence = 45.0
    _add_breakdown(breakdown, "quality", "基础质量", quality, "候选词通过基础标准后获得初始质量分。")

    if len(kw) < 8 or len(kw) > 90:
        quality -= 0.25
        noise += 20
        reasons.append("bad_length")
        _add_breakdown(breakdown, "noise", "长度异常", -0.25, "过短或过长的表达更容易是噪音。")
    if len(terms) < 2:
        quality -= 0.30
        noise += 30
        reasons.append("too_short_phrase")
        _add_breakdown(breakdown, "noise", "词组过短", -0.30, "少于两个词时通常难以判断真实搜索需求。")
    if 2 <= len(terms) <= 6:
        quality += 0.06
        demand += 8
        _add_breakdown(breakdown, "quality", "表达长度合适", 0.06, "2-6 个词通常更适合作为可追踪线索。")
    if len(terms) > 8:
        quality -= 0.12
        noise += 12
        reasons.append("too_long")
        _add_breakdown(breakdown, "noise", "表达过长", -0.12, "过长表达可能只是标题或一次性页面残留。")

    if any(term in kw for term in BAD_KEYWORD_TERMS):
        quality -= 0.45
        noise += 45
        reasons.append("blocked_noise_term")
        _add_breakdown(breakdown, "noise", "命中噪音词", -0.45, "登录、社交平台、官网门户等词会降低候选质量。")
    if any(re.search(pattern, kw) for pattern in TITLE_RESIDUE_PATTERNS):
        quality -= 0.70
        noise += 55
        reasons.append("title_or_brand_residue")
        _add_breakdown(breakdown, "noise", "疑似标题残留", -0.70, "像网页标题、品牌标题或评论标题的表达会被强降权。")
    if terms and terms[-1] in BAD_SINGLE_MODIFIERS:
        quality -= 0.25
        noise += 20
        reasons.append("bad_modifier")
        _add_breakdown(breakdown, "noise", "坏修饰词", -0.25, "结尾修饰词无法形成清晰搜索需求。")
    if re.search(r"\b(best|top|free|202[0-9])\b", kw):
        quality -= 0.08
        noise += 8
        reasons.append("listicle_noise")
        _add_breakdown(breakdown, "noise", "榜单/年份噪音", -0.08, "best、top、free、年份词可能带来榜单噪音。")
    if len(set(terms)) < len(terms):
        quality -= 0.06
        noise += 8
        reasons.append("repeated_terms")
        _add_breakdown(breakdown, "noise", "重复词", -0.06, "重复词会降低表达质量。")

    has_tool = bool(term_set & TOOL_INTENT_TERMS or any(term in kw for term in TOOL_INTENT_TERMS))
    has_commercial = bool(term_set & COMMERCIAL_TERMS or any(term in kw for term in COMMERCIAL_TERMS))
    commercial_hits = 0
    if has_tool:
        quality += 0.16
        demand += 24
        commercial_hits += 1
        reasons.append("task_intent")
        _add_breakdown(breakdown, "demand", "任务/工具意图", 0.16, "包含工具、模板、计算器、追踪器、自动化等任务词。")
    if has_commercial:
        quality += 0.14
        demand += 22
        commercial_hits += 1
        reasons.append("commercial_signal")
        _add_breakdown(breakdown, "demand", "商业/行业信号", 0.14, "包含行业、付费、合规、税务、客户或业务场景词。")
    if any(term in kw for term in {"late", "fee", "overdue", "deadline", "renewal", "audit", "risk", "penalty", "payment", "compliance", "tax"}):
        quality += 0.08
        demand += 12
        reasons.append("pay_trigger")
        _add_breakdown(breakdown, "demand", "付费触发", 0.08, "包含罚金、截止、审计、支付、合规等更接近付费触发的词。")
    if commercial_hits == 0:
        quality -= 0.18
        demand -= 18
        reasons.append("no_commercial_signal")
        _add_breakdown(breakdown, "demand", "缺少商业信号", -0.18, "没有明显任务词或商业场景词。")

    if seed_l and kw == seed_l:
        quality -= 0.20
        reasons.append("same_as_seed")
        _add_breakdown(breakdown, "quality", "和输入对象相同", -0.20, "没有产生新的可验证表达。")
    if seed_l and seed_l.replace(" ", "") in kw.replace(" ", "") and kw.replace(" ", "").count(seed_l.replace(" ", "")) > 1:
        quality -= 0.45
        noise += 35
        reasons.append("seed_repeated_or_brand_echo")
        _add_breakdown(breakdown, "noise", "输入对象重复", -0.45, "输入对象被重复拼接，可能是品牌回声或标题残留。")
    if seed_terms and len(seed_terms & term_set) >= max(1, min(2, len(seed_terms))):
        quality += 0.08
        source_confidence += 12
        reasons.append("seed_overlap")
        _add_breakdown(breakdown, "source", "输入对象相关", 0.08, "和输入对象保留了足够语义重叠。")
    if seed_terms and added_words and not (added_words & GOOD_MODIFIERS):
        quality -= 0.30
        noise += 20
        reasons.append("weak_added_modifier")
        _add_breakdown(breakdown, "noise", "新增修饰词偏弱", -0.30, "新增词没有落在已知的任务、商业或行业修饰词上。")

    source_bonus = EARLY_SOURCE_BONUS.get(source, 0.04)
    quality += source_bonus
    source_confidence += source_bonus * 100
    _add_breakdown(breakdown, "source", "来源基础可信度", source_bonus, "不同线索模型有不同的基础可信加权。")
    if source in TREND_SOURCES:
        trend += 28
        _add_breakdown(breakdown, "trend", "变化/趋势来源", 0.28, "来源模型偏向新页面、站点变化或早期信号。")
    if evidence.get("is_new_url") or evidence.get("first_seen_at"):
        quality += 0.18
        trend += 24
        reasons.append("fresh_url")
        _add_breakdown(breakdown, "trend", "新 URL / 首次发现", 0.18, "证据显示这是新出现或首次发现的对象。")
    if evidence.get("variant") in {"allintitle_after", "site_after"}:
        quality += 0.10
        trend += 12
        _add_breakdown(breakdown, "trend", "时间限定搜索", 0.10, "搜索条件偏向新近页面或标题变化。")
    if evidence.get("provider") in {"serpapi", "zenserp", "scaleserp"}:
        quality += 0.04
        source_confidence += 8
        _add_breakdown(breakdown, "source", "搜索供应商", 0.04, "来自结构化 SERP 供应商的结果。")
    if source_domain and any(domain in source_domain for domain in WEAK_SOURCE_DOMAINS):
        quality -= 0.25
        source_confidence -= 25
        reasons.append("weak_source_domain")
        _add_breakdown(breakdown, "source", "弱来源域名", -0.25, "部分目录、社交或评论站点容易产生标题噪音。")

    quality = round(_clamp(quality), 3)
    demand = max(demand, quality * 100)
    trend = max(trend, quality * 45)
    demand = round(_clamp(demand, 0, 100), 1)
    trend = round(_clamp(trend, 0, 100), 1)
    noise = round(_clamp(noise, 0, 100), 1)
    source_confidence = round(_clamp(source_confidence, 0, 100), 1)
    severe_reasons = {"blocked_noise_term", "title_or_brand_residue", "seed_repeated_or_brand_echo"}
    weak_reasons = {"weak_added_modifier", "no_commercial_signal", "weak_source_domain"}
    reason_set = set(reasons)
    gate = "reject" if quality < 0.45 or bool(severe_reasons & reason_set) or (quality < 0.68 and bool(weak_reasons & reason_set)) else "pass" if quality >= 0.68 else "watch"
    return {
        "candidate_quality_score": quality,
        "demand_signal_score": demand,
        "trend_signal_score": trend,
        "noise_risk_score": noise,
        "source_confidence_score": source_confidence,
        "gate": gate,
        "reasons": reasons,
        "breakdown": breakdown,
        "formula": "候选质量分 = 文本质量 + 商业/任务意图 + 来源可信 + 新鲜度 - 噪音风险；需求/趋势为同一评分框架下的拆分信号。",
    }


def score_candidate(keyword: str, source: str, evidence: dict[str, Any] | None = None, base: float = 0.0) -> float:
    return score_candidate_detail(keyword, source=source, evidence=evidence, base=base)["candidate_quality_score"]


def keyword_quality_score(seed: str, keyword: str, source_domain: str = "") -> tuple[float, list[str]]:
    result = score_candidate_detail(keyword, source="four_find", seed=seed, source_domain=source_domain)
    return result["candidate_quality_score"], result["reasons"]


def candidate_is_importable(seed: str, keyword: str, source_domain: str = "") -> bool:
    return score_candidate_detail(keyword, source="four_find", seed=seed, source_domain=source_domain)["gate"] == "pass"
