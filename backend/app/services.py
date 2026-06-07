from __future__ import annotations
import json, re, itertools, os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests
from sqlalchemy.orm import Session
from . import models
ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SETTINGS = {
    "SEARXNG_URL": "http://127.0.0.1:8080",
    "SEARXNG_URLS": "",
    "SEARXNG_ENDPOINTS": "[]",
    "SEARXNG_API_TOKEN": "",
    "SEARXNG_ENGINES": "bing",
    "BRAVE_API_KEY": "",
    "BRAVE_API_KEYS": "",
    "TAVILY_API_KEY": "",
    "TAVILY_API_KEYS": "",
    "LLM_PROVIDER": "",
    "LLM_API_KEY": "",
    "LLM_PRIMARY_BASE_URL": "",
    "LLM_PRIMARY_PROVIDER": "",
    "LLM_PRIMARY_MODEL": "",
    "LLM_PRIMARY_API_KEY": "",
    "LLM_FALLBACKS": "[]",
    "AUTO_RUN_ENABLED": "true",
    "AUTO_RUN_INTERVAL_MINUTES": "360",
    "AUTO_RUN_LIMIT": "6",
    "MIN_ACTION_SCORE": "74",
    "REQUIRE_SOCIAL_FOR_ACTION": "false",
    "COLLECT_SOCIAL_EVIDENCE": "false",
    "BLOCKED_TERMS": "booking,best",
    "FOUR_FIND_AUTO_ENABLED": "true",
    "FOUR_FIND_AUTO_SEEDS": "invoice calculator,appointment template,compliance tracker",
    "FOUR_FIND_AUTO_DOMAINS": "",
    "FOUR_FIND_IMPORT_LIMIT": "6",
    "FOUR_FIND_REWRITE_ON_SERP_REJECT": "false",
    "FOUR_FIND_REWRITE_LIMIT": "4",
    "FOUR_FIND_SERP_STRATEGY_ENABLED": "true",
    "FOUR_FIND_SERP_VARIANT_LIMIT": "2",
    "SERP_PROVIDER_ORDER": "searxng,brave,tavily",
    "SERP_PROVIDER_ATTEMPT_LIMIT": "3",
    "SERP_ROTATION_STRATEGY": "failover",
}
DEFAULT_ROOTS = [
    ("invoice", "function"), ("calculator", "tool"), ("template", "tool"),
    ("shopify", "vertical"), ("woocommerce", "vertical"), ("quickbooks", "vertical"),
    ("reconciliation", "pain"), ("tracker", "tool"), ("generator", "tool"),
    ("appointment", "vertical"), ("compliance", "pain"), ("dashboard", "tool"),
    ("contractor", "vertical"), ("clinic", "vertical"), ("rental", "vertical"),
]
INTENT_WORDS = {"template":"seo_tool", "calculator":"seo_tool", "generator":"seo_tool", "tracker":"workflow_tool", "dashboard":"workflow_saas", "integration":"workflow_saas", "automation":"workflow_saas", "reconciliation":"workflow_saas"}
STRONG_DOMAINS = ("google.com","microsoft.com","adobe.com","shopify.com","intuit.com","hubspot.com","salesforce.com","wikipedia.org","amazon.com","booking.com","expedia.com","kayak.com")
FORUM_DOMAINS = ("reddit.com","news.ycombinator.com","stackoverflow.com","quora.com","community.","forum.")
WEAK_HINTS = ("free", "blog", "post", "forum", "reddit", "template", "spreadsheet", "pdf", "docs", "github")
BLOCKED_AMBIGUOUS_ROOTS = {"booking"}


def setting(db: Session, key: str) -> str:
    env_value = os.environ.get(key)
    if env_value:
        return env_value
    row = db.get(models.Setting, key)
    return row.value if row else DEFAULT_SETTINGS.get(key, "")

def init_defaults(db: Session):
    for k,v in DEFAULT_SETTINGS.items():
        default_value = os.environ.get(k, v)
        if not db.get(models.Setting, k):
            db.add(models.Setting(key=k, value=default_value, secret=k.endswith("KEY") or k.endswith("KEYS") or k.endswith("TOKEN") or k in {"LLM_FALLBACKS"}))
    for term, cat in DEFAULT_ROOTS:
        if not db.query(models.Root).filter_by(term=term).first():
            db.add(models.Root(term=term, category=cat, weight=1.0))
    db.commit()

def classify_intent(query: str) -> str:
    q = query.lower()
    for w, intent in INTENT_WORDS.items():
        if w in q:
            return intent
    return "search_demand"

def compatible(a: models.Root, b: models.Root) -> bool:
    if a.term == b.term: return False
    cats = {a.category, b.category}
    return ("tool" in cats and ("vertical" in cats or "pain" in cats or "function" in cats)) or ("function" in cats and "vertical" in cats)

def ordered_query(a: models.Root, b: models.Root) -> tuple[str, list[str]]:
    # Put market/entity/pain first and tool/modifier last. This avoids bad queries like
    # "calculator invoice" that collapse into generic calculator SERPs.
    priority = {"vertical": 0, "function": 1, "pain": 2, "tool": 3}
    first, second = sorted([a, b], key=lambda r: (priority.get(r.category, 9), r.term))
    return f"{first.term} {second.term}", [first.term, second.term]

def discover_keywords(db: Session, limit=24, roots: list[str] | None = None) -> list[models.Keyword]:
    q = db.query(models.Root).filter_by(enabled=True)
    if roots:
        q = q.filter(models.Root.term.in_(roots))
    root_rows = q.order_by(models.Root.weight.desc(), models.Root.term).all()
    candidates = []
    seen_queries = set()
    blocked = set(BLOCKED_AMBIGUOUS_ROOTS)
    blocked.update(t.strip().lower() for t in setting(db, "BLOCKED_TERMS").split(",") if t.strip())
    root_rows = [r for r in root_rows if r.term.lower() not in blocked]
    for a,b in itertools.combinations(root_rows, 2):
        if compatible(a,b):
            base, terms = ordered_query(a, b)
            for query in [base, f"{base} software"]:
                if query not in seen_queries:
                    seen_queries.add(query)
                    candidates.append((query, terms))
    out = []
    for query, terms in candidates[:limit]:
        row = db.query(models.Keyword).filter_by(query=query).first()
        if not row:
            row = models.Keyword(query=query, source="root_combo", root_terms=json.dumps(terms), intent=classify_intent(query))
            db.add(row); db.flush()
        out.append(row)
    db.commit()
    return out

def discover_keywords_four_find(db: Session, limit=24, seeds: list[str] | None = None) -> list[models.Keyword]:
    """Discover/import keywords through the Four-Find service path.

    This keeps discovery as a backend/API capability rather than a shell script.
    """
    from . import four_find
    raw_domains = setting(db, "FOUR_FIND_AUTO_DOMAINS") or ""
    domains = [x.strip() for x in re.split(r"[\n,]+", raw_domains) if x.strip()]
    if seeds is None:
        raw = setting(db, "FOUR_FIND_AUTO_SEEDS") or ""
        seeds = [x.strip() for x in raw.split(",") if x.strip()]
    if not seeds and not domains:
        return []
    try:
        import_limit = int(setting(db, "FOUR_FIND_IMPORT_LIMIT") or str(limit))
    except Exception:
        import_limit = limit
    out: list[models.Keyword] = []
    seen: set[str] = set()
    # Site→Keyword and Site→Site loop: learned domains from feedback are now
    # first-class automatic discovery seeds, not just passive records.
    for domain in domains[:max(1, limit // 2)]:
        four_find.find_keywords_from_site(db, domain, searxng_search, limit=8)
        similar = four_find.find_similar_sites(db, domain, searxng_search, limit=4)
        for site in similar[:2]:
            four_find.find_keywords_from_site(db, site.similar_domain, searxng_search, limit=4)
        for kw in four_find.import_discovered_keywords(db, limit=max(1, min(import_limit, limit))):
            if kw.query not in seen:
                seen.add(kw.query); out.append(kw)
            if len(out) >= limit:
                return out
    per_seed = max(1, min(import_limit, limit) // max(1, len(seeds)))
    for seed in seeds:
        four_find.run_four_find_and_import(db, seed, searxng_search, depth=2, import_limit=per_seed)
        rows = db.query(models.Keyword).filter(models.Keyword.source.like("four_find:%")).order_by(models.Keyword.created_at.desc()).limit(limit).all()
        for row in rows:
            if row.query not in seen:
                seen.add(row.query)
                out.append(row)
            if len(out) >= limit:
                return out
    return out


_ROTATION_STATE: dict[str, int] = {}

def _split_multi_value(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[\n,]+", value)
    return [p.strip() for p in parts if p.strip() and not p.strip().startswith("#")]

def serp_rotation_strategy(db: Session) -> str:
    raw = (setting(db, "SERP_ROTATION_STRATEGY") or "failover").strip().lower()
    return "round_robin" if raw in {"round_robin", "sequential", "顺序轮询"} else "failover"

def _maybe_rotate(db: Session, key: str, values: list):
    if not values:
        return values
    if serp_rotation_strategy(db) != "round_robin":
        return values
    idx = _ROTATION_STATE.get(key, 0) % len(values)
    _ROTATION_STATE[key] = idx + 1
    return values[idx:] + values[:idx]

def _rotating_values(db: Session, multi_key: str, single_key: str = "") -> list[str]:
    values = _split_multi_value(setting(db, multi_key))
    if not values and single_key:
        single = setting(db, single_key).strip()
        if single:
            values = [single]
    if not values:
        return []
    return _maybe_rotate(db, multi_key, values)

def searxng_urls(db: Session) -> list[str]:
    return [e["url"] for e in searxng_endpoints(db)]

def searxng_endpoints(db: Session) -> list[dict]:
    """Return SearXNG endpoints as {url, api_token} with rotation applied.

    New config uses SEARXNG_ENDPOINTS JSON so each URL can carry its own
    X-API-TOKEN. Old SEARXNG_URLS/SEARXNG_URL + SEARXNG_API_TOKEN remain as
    fallback for existing deployments.
    """
    raw = setting(db, "SEARXNG_ENDPOINTS") or ""
    endpoints: list[dict] = []
    if raw and not raw.startswith("***"):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        url = str(item.get("url") or "").strip().rstrip("/")
                        token = str(item.get("api_token") or item.get("token") or "").strip()
                        use_builtin = bool(item.get("use_builtin_engines", True))
                        engines = str(item.get("engines") or "").strip()
                    else:
                        url = str(item or "").strip().rstrip("/")
                        token = ""
                        use_builtin = True
                        engines = ""
                    if url:
                        endpoints.append({"url": url, "api_token": token, "use_builtin_engines": use_builtin, "engines": engines})
        except Exception:
            endpoints = []
    if not endpoints:
        legacy_token = setting(db, "SEARXNG_API_TOKEN") or ""
        urls = _rotating_values(db, "SEARXNG_URLS", "SEARXNG_URL")
        legacy_engines = setting(db, "SEARXNG_ENGINES") or ""
        endpoints = [{"url": u.rstrip("/"), "api_token": legacy_token, "use_builtin_engines": not bool(legacy_engines), "engines": legacy_engines} for u in urls if u.strip()]
    if not endpoints:
        return []
    return _maybe_rotate(db, "SEARXNG_ENDPOINTS", endpoints)

def rotating_api_keys(db: Session, multi_key: str, single_key: str) -> list[str]:
    return _rotating_values(db, multi_key, single_key)

def searxng_search(db: Session, query: str, categories="general", limit=10) -> list[dict]:
    endpoints = searxng_endpoints(db)
    if not endpoints:
        return []
    last_error = ""
    for endpoint in endpoints:
        base = endpoint["url"]
        headers = {"Accept": "application/json"}
        token = endpoint.get("api_token") or ""
        if token:
            headers["X-API-TOKEN"] = token
        try:
            params={"q": query, "format":"json", "language":"en"}
            engines = endpoint.get("engines") or ""
            if not endpoint.get("use_builtin_engines", True) and engines:
                params["engines"] = engines
            elif endpoint.get("use_builtin_engines", True):
                pass
            elif categories:
                params["categories"] = categories
            r = requests.get(f"{base}/search", params=params, headers=headers, timeout=12)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])[:limit]
            for item in results:
                item["provider_base"] = base
            return results
        except Exception as e:
            last_error = f"{base}: {e}"
            continue
    return [{"title":"SearXNG error", "url":"", "content":last_error, "engine":"error"}]

def brave_search(db: Session, query: str, limit=10) -> list[dict]:
    keys = rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")
    if not keys:
        return []
    last_error = ""
    for key in keys:
      try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": min(max(limit, 1), 20), "search_lang": "en"},
            headers={"Accept": "application/json", "X-Subscription-Token": key},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        out=[]
        for item in (data.get("web", {}) or {}).get("results", [])[:limit]:
            out.append({
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "content": item.get("description") or "",
                "engine": "brave",
            })
        return out
      except Exception as e:
        last_error = str(e)
        continue
    return [{"title":"Brave error", "url":"", "content":last_error, "engine":"error"}]

def tavily_search(db: Session, query: str, limit=10) -> list[dict]:
    keys = rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY")
    if not keys:
        return []
    last_error = ""
    for key in keys:
      try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": min(max(limit, 1), 10), "search_depth": "basic", "include_answer": False},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        out=[]
        for item in data.get("results", [])[:limit]:
            out.append({
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "content": item.get("content") or "",
                "engine": "tavily",
            })
        return out
      except Exception as e:
        last_error = str(e)
        continue
    return [{"title":"Tavily error", "url":"", "content":last_error, "engine":"error"}]

def available_serp_providers(db: Session) -> list[str]:
    order = [x.strip().lower() for x in (setting(db, "SERP_PROVIDER_ORDER") or "searxng").split(",") if x.strip()]
    out=[]
    for p in order:
        if p == "searxng":
            out.append(p)
        elif p == "brave" and rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY"):
            out.append(p)
        elif p == "tavily" and rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY"):
            out.append(p)
    return out or ["searxng"]

def provider_search(db: Session, provider: str, query: str, limit=10) -> list[dict]:
    if provider == "brave": return brave_search(db, query, limit)
    if provider == "tavily": return tavily_search(db, query, limit)
    return searxng_search(db, query, limit=limit)

def domain(url: str) -> str:
    try: return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception: return ""

def query_overlap(query: str, result: dict) -> float:
    q_terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in {"best", "free", "software", "tool", "online"}]
    hay = " ".join([result.get("title") or "", result.get("url") or "", result.get("content") or result.get("snippet") or ""]).lower()
    if not q_terms: return 1.0
    return sum(1 for t in q_terms if t in hay) / len(q_terms)

def gap_tags_for(result: dict, query: str = "") -> tuple[list[str], float]:
    title = (result.get("title") or "").lower(); url = result.get("url") or ""; snip = (result.get("content") or result.get("snippet") or "").lower(); d = domain(url)
    tags, score = [], 0.0
    if query and query_overlap(query, result) < 0.5: tags.append("query_mismatch"); score -= 0.45
    if any(x in d for x in FORUM_DOMAINS): tags.append("forum_heavy"); score += 0.25
    if any(x in d for x in STRONG_DOMAINS): tags.append("strong_brand"); score -= 0.25
    if any(x in title+" "+snip+" "+url.lower() for x in WEAK_HINTS): tags.append("weak_content_or_template"); score += 0.2
    if len(snip) < 80: tags.append("thin_snippet"); score += 0.1
    if re.search(r"\b(best|top|free)\b", title): tags.append("listicle_or_free_intent"); score += 0.1
    return sorted(set(tags)), max(0.0, min(1.0, 0.45 + score))

def serp_query_variants(query: str) -> list[str]:
    """Generate provider-specific search query variants for long-tail demand terms."""
    q = re.sub(r"\s+", " ", query.lower()).strip()
    variants = [q]
    # Exclude obvious sources of SERP drift for appointment/compliance/local terms.
    exclude_gov = f'{q} -site:.gov -site:*.gov'
    variants.append(exclude_gov)
    if any(w in q for w in ["template", "form", "policy"]):
        variants += [
            f'"{q}" template OR form',
            f'{q} examples template form -site:.gov',
        ]
    elif any(w in q for w in ["calculator", "invoice", "fee", "tax"]):
        variants += [
            f'"{q}" calculator tool',
            f'{q} tool calculator -site:.gov',
        ]
    elif any(w in q for w in ["tracker", "compliance", "dashboard"]):
        variants += [
            f'"{q}" software dashboard',
            f'{q} template spreadsheet software -site:.gov',
        ]
    else:
        variants.append(f'"{q}"')
    out=[]; seen=set()
    for v in variants:
        v = re.sub(r"\s+", " ", v).strip()
        if v and v not in seen:
            seen.add(v); out.append(v)
    return out

def _serp_meta_from_items(items: list[dict], original_query: str, search_query: str, provider: str = "searxng") -> dict:
    evaluated=[]
    for item in items[:10]:
        tags, weakness = gap_tags_for(item, original_query)
        evaluated.append({"item": item, "tags": tags, "weakness": weakness})
    mismatch = sum(1 for e in evaluated if "query_mismatch" in e["tags"])
    strong = sum(1 for e in evaluated if "strong_brand" in e["tags"])
    relevant = len(evaluated) - mismatch
    avg_gap = sum(e["weakness"] for e in evaluated) / max(1, len(evaluated))
    # selection_score rewards relevance first, then useful weakness; penalizes strong-brand SERPs.
    selection_score = round((relevant / max(1, len(evaluated))) * 0.65 + avg_gap * 0.35 - strong * 0.03, 3)
    return {"provider": provider, "query": search_query, "results": len(evaluated), "relevant": relevant, "mismatch": mismatch, "strong": strong, "avg_gap": round(avg_gap, 3), "selection_score": selection_score, "evaluated": evaluated}

def choose_best_serp_items(db: Session, original_query: str, limit: int = 10) -> tuple[list[dict], dict]:
    try:
        variant_limit = int(setting(db, "FOUR_FIND_SERP_VARIANT_LIMIT") or "2")
    except Exception:
        variant_limit = 2
    variants = serp_query_variants(original_query)[:max(1, variant_limit)]
    providers = available_serp_providers(db)
    try:
        attempt_limit = int(setting(db, "SERP_PROVIDER_ATTEMPT_LIMIT") or "3")
    except Exception:
        attempt_limit = 3
    metas=[]
    attempts=0
    for variant in variants:
        for provider in providers:
            if attempts >= max(1, attempt_limit):
                break
            attempts += 1
            items = provider_search(db, provider, variant, limit=limit)
            metas.append(_serp_meta_from_items(items, original_query, variant, provider))
        if attempts >= max(1, attempt_limit):
            break
    best = sorted(metas, key=lambda m: (m["selection_score"], m["relevant"], m["avg_gap"]), reverse=True)[0] if metas else _serp_meta_from_items([], original_query, original_query)
    best["attempts"] = [{k:v for k,v in m.items() if k != "evaluated"} for m in metas]
    return [e["item"] for e in best.get("evaluated", [])], {k:v for k,v in best.items() if k != "evaluated"}

def run_serp(db: Session, keyword: models.Keyword) -> list[models.SerpResult]:
    rows, meta = run_serp_with_strategy(db, keyword)
    return rows

def run_serp_with_strategy(db: Session, keyword: models.Keyword) -> tuple[list[models.SerpResult], dict]:
    db.query(models.SerpResult).filter_by(keyword_id=keyword.id).delete()
    if (setting(db, "FOUR_FIND_SERP_STRATEGY_ENABLED") or "false").lower() in {"1", "true", "yes", "on"}:
        results, strategy_meta = choose_best_serp_items(db, keyword.query, limit=10)
    else:
        results = searxng_search(db, keyword.query, limit=10)
        strategy_meta = {"query": keyword.query, "strategy": "disabled"}
    rows = []
    for i, item in enumerate(results, 1):
        tags, weakness = gap_tags_for(item, keyword.query)
        row = models.SerpResult(keyword_id=keyword.id, rank=i, title=item.get("title") or "", url=item.get("url") or "", snippet=item.get("content") or item.get("snippet") or "", domain=domain(item.get("url") or ""), gap_tags=json.dumps(tags), weakness_score=weakness)
        db.add(row); rows.append(row)
    db.commit()
    return rows, strategy_meta

def rewrite_query_candidates(query: str) -> list[str]:
    """Generate API/service-level query rewrites for SERP-rejected Four-Find keywords.

    These rewrites are not root-combo guesses. They are task-intent rewrites designed
    to disambiguate vague long-tails after SERP mismatch.
    """
    q = re.sub(r"\s+", " ", query.lower()).strip()
    candidates: list[str] = []
    if "appointment" in q:
        candidates += [
            "clinic appointment reminder template",
            "patient appointment form template",
            "appointment cancellation policy template",
            "appointment reschedule email template",
            "dental appointment reminder template",
            "patient appointment intake form template",
        ]
    if "invoice" in q or "calculator" in q:
        candidates += [
            "invoice late fee calculator",
            "overdue invoice interest calculator",
            "late payment fee calculator",
            "invoice payment reminder calculator",
            "contractor invoice estimate calculator",
            "rental late fee calculator",
        ]
    if "compliance" in q or "tracker" in q:
        candidates += [
            "compliance deadline tracking software",
            "vendor compliance tracking spreadsheet",
            "employee training compliance tracker",
            "audit compliance checklist tracker",
            "permit renewal compliance tracker",
            "compliance report dashboard template",
        ]
    if not candidates:
        terms = [t for t in re.findall(r"[a-z0-9]+", q) if t not in {"software", "tool", "online", "free"}]
        base = " ".join(terms[:4])
        candidates += [f"{base} template", f"{base} calculator", f"{base} tracker"]
    out=[]; seen=set()
    for c in candidates:
        c = re.sub(r"\s+", " ", c).strip()
        if c and c != q and c not in seen:
            seen.add(c); out.append(c)
    return out

def recover_serp_rejects(db: Session, limit: int = 8) -> dict:
    """Rewrite SERP-rejected Four-Find keywords and only generate cards for admissible SERPs."""
    from . import four_find
    source_rows = db.query(models.Keyword).filter(
        models.Keyword.status == "serp_reject",
        models.Keyword.source.like("four_find:%"),
    ).order_by(models.Keyword.created_at.desc()).limit(limit).all()
    created=[]; admitted=[]; rejected=[]; cards=[]
    for src in source_rows:
        rewrites = rewrite_query_candidates(src.query)
        source_admitted = False
        for rq in rewrites[:2]:
            if not four_find.candidate_is_importable(src.query, rq):
                rejected.append({"source": src.query, "rewrite": rq, "reason": "candidate_quality"})
                continue
            kw = db.query(models.Keyword).filter_by(query=rq).first()
            if not kw:
                kw = models.Keyword(query=rq, source="four_find:rewrite", root_terms=json.dumps([src.query]), intent=classify_intent(rq))
                db.add(kw); db.commit(); db.refresh(kw)
                created.append(rq)
            if kw.status in {"action", "watch"}:
                continue
            serp, strategy_meta = run_serp_with_strategy(db, kw)
            ok, gate = serp_admissibility(serp)
            if not ok:
                kw.status = "serp_reject"
                db.commit()
                rejected.append({"source": src.query, "rewrite": rq, "serp_strategy": strategy_meta, **gate})
                continue
            card = make_card(db, kw)
            cards.append(card)
            admitted.append({"source": src.query, "rewrite": rq, "card_id": card.id, "verdict": card.verdict, "score": card.score})
            src.status = "rewrite_admitted"
            db.commit()
            source_admitted = True
            break
        if not source_admitted:
            src.status = "rewrite_exhausted"
            db.commit()
    return {"source_keywords": len(source_rows), "created_rewrites": created, "admitted": admitted, "rejected": rejected[:20], "cards": len(cards)}

def serp_admissibility(serp: list[models.SerpResult]) -> tuple[bool, dict]:
    """Gate keywords before card generation.

    Four-Find can produce useful long tails, but SearXNG/SERP may still interpret them
    as government pages, brand pages, or unrelated local appointment flows. Those
    should not become opportunity cards; they should remain candidates for review.
    """
    if not serp:
        return False, {"reason": "no_serp"}
    top = serp[:10]
    mismatch = sum(1 for s in top if "query_mismatch" in (s.gap_tags or ""))
    strong = sum(1 for s in top if "strong_brand" in (s.gap_tags or ""))
    commercial = sum(1 for s in top if _commercial_serp_signal(s))
    informational = sum(1 for s in top if _informational_serp_signal(s))
    relevant = len(top) - mismatch
    avg_gap = sum(s.weakness_score for s in top) / max(1, len(top))
    commercial_required = max(2, min(4, len(top)//3))
    ok = (
        relevant >= 5
        and mismatch <= max(3, len(top)//2)
        and avg_gap >= 0.32
        and commercial >= commercial_required
        and informational <= max(2, len(top)//3)
    )
    reason = "ok" if ok else "weak_or_mismatched_serp"
    if not ok and commercial < commercial_required:
        reason = "no_commercial_serp_signal"
    elif not ok and informational > max(2, len(top)//3):
        reason = "informational_or_dictionary_serp"
    return ok, {"relevant": relevant, "mismatch": mismatch, "strong": strong, "commercial": commercial, "informational": informational, "avg_gap": round(avg_gap, 3), "reason": reason}

def mark_four_find_serp_reject(db: Session, keyword: models.Keyword, gate: dict) -> None:
    """Feed SERP-gate failures back into Four-Find discovery memory.

    A keyword that looks commercially plausible but produces non-commercial or
    mismatched SERP should not be retried/imported every daily run.
    """
    if not keyword.source.startswith("four_find:"):
        return
    try:
        roots = json.loads(keyword.root_terms or "[]")
    except Exception:
        roots = []
    reason = gate.get("reason") or "serp_reject"
    for seed in roots:
        exp = db.query(models.DiscoveryExpansion).filter_by(seed_keyword=seed, expanded_keyword=keyword.query).first()
        if exp:
            exp.score = max(0.0, min(1.0, (exp.score or 0.0) - 0.35))
            exp.status = "rejected"
        ck = db.query(models.CompetitorKeyword).filter_by(competitor_domain=seed, discovered_keyword=keyword.query).first()
        if ck:
            ck.score = max(0.0, min(1.0, (ck.score or 0.0) - 0.35))
            ck.status = "rejected"
    keyword.status = "serp_reject"
    keyword.score = 0.0
    keyword.intent = f"serp_reject:{reason}"[:80]
    db.commit()

def _commercial_serp_signal(s: models.SerpResult) -> bool:
    text = f"{s.domain} {s.title} {s.url} {s.snippet}".lower()
    return any(t in text for t in (
        "calculator", "template", "generator", "tool", "software", "app",
        "dashboard", "tracker", "checklist", "form", "spreadsheet", "excel",
        "download", "pricing", "free", "online", "invoice", "notice",
        "reminder", "estimate", "converter", "builder",
    ))

def _informational_serp_signal(s: models.SerpResult) -> bool:
    text = f"{s.domain} {s.title} {s.url} {s.snippet}".lower()
    return any(d in s.domain for d in (
        "dictionary.com", "merriam-webster.com", "dictionary.cambridge.org",
        "collinsdictionary.com", "wikipedia.org", "britannica.com", "wiktionary.org",
    )) or any(t in text for t in (
        "definition", "meaning", "dictionary", "encyclopedia", "what is", "overview",
    ))

def collect_social(db: Session, keyword: models.Keyword) -> list[models.SocialEvidence]:
    db.query(models.SocialEvidence).filter_by(keyword_id=keyword.id).delete()
    if (setting(db, "COLLECT_SOCIAL_EVIDENCE") or "false").lower() not in {"1", "true", "yes", "on"}:
        db.commit(); return []
    rows=[]
    for suffix, platform in [(" site:reddit.com", "reddit"), (" site:news.ycombinator.com", "hn")]:
        for item in searxng_search(db, keyword.query + suffix, limit=2):
            if not item.get("url"): continue
            row=models.SocialEvidence(keyword_id=keyword.id, platform=platform, url=item.get("url",""), title=item.get("title",""), snippet=item.get("content") or "", pain_tags=json.dumps(["search_mention"]))
            db.add(row); rows.append(row)
    db.commit(); return rows

def analyze_competitors(db: Session, keyword: models.Keyword) -> list[models.CompetitorPage]:
    db.query(models.CompetitorPage).filter_by(keyword_id=keyword.id).delete()
    serp = db.query(models.SerpResult).filter_by(keyword_id=keyword.id).order_by(models.SerpResult.rank).limit(5).all()
    rows=[]
    for s in serp:
        tags = json.loads(s.gap_tags or "[]")
        if "strong_brand" not in tags:
            row=models.CompetitorPage(keyword_id=keyword.id, url=s.url, domain=s.domain, title=s.title, weakness_tags=json.dumps(tags), content_excerpt=s.snippet[:1000])
            db.add(row); rows.append(row)
    db.commit(); return rows

def monetization(query: str, intent: str) -> tuple[str, float]:
    q=query.lower()
    if any(w in q for w in ["calculator","template","generator"]): return "SEO tool + ads/affiliate/lead magnet", 0.75
    if any(w in q for w in ["integration","sync","automation","dashboard","reconciliation"]): return "micro-SaaS subscription", 0.8
    if "compliance" in q: return "leadgen + paid report", 0.65
    return "content/tool affiliate", 0.5

def business_profile(query: str, intent: str, monetization_type: str) -> dict:
    """Business-layer interpretation for opportunity cards.

    This turns SERP/search evidence into a decision-oriented business brief:
    who cares, what triggers payment, the wedge, and the first validation step.
    """
    q = query.lower()
    icp = "SEO traffic operator / niche tool builder"
    pain = "User wants a faster self-serve answer than generic search results."
    pay_trigger = "Pays when the output saves time, avoids mistakes, or can be reused in workflow."
    wedge = "Single-purpose tool with clearer UX and better long-tail coverage than generic content pages."
    revenue_path = "SEO entry → free utility → email capture → paid template/tool bundle."
    pricing = "$9-$29 one-time template/tool pack, or affiliate/leadgen if purchase intent is weak."
    commercial_mvp = "A focused landing page with one paid/exportable output that tests purchase intent before product depth."
    first_sale_test = [
        "Publish the exact commercial offer on the landing page.",
        "Add a checkout/waitlist button before building extra product depth.",
        "Measure purchase intent: checkout clicks, email capture, reply rate, or paid preorders.",
    ]
    gtm = "Long-tail SEO + comparison pages + template/tool directories."
    commercial_score = 0.55
    business_type = "content/tool affiliate"
    if any(w in q for w in ["appointment", "patient", "clinic", "dental", "salon"]):
        icp = "Small clinic / appointment-heavy local service operator"
        pain = "They need repeatable appointment templates, reminders, cancellation/reschedule flows, or intake forms."
        pay_trigger = "Pays when no-shows, admin time, or inconsistent communication create visible cost."
        wedge = "Template + workflow pack for a narrow vertical, not a generic scheduling blog post."
        business_type = "template pack → leadgen → lightweight SaaS"
        commercial_mvp = "A vertical template/workflow pack with download gate and paid customization CTA."
        revenue_path = "Free template → email capture → paid workflow pack → setup/service upsell."
        pricing = "$19-$79 template/workflow pack; $199-$499 setup service if vertical pain is strong."
        first_sale_test = ["Sell a 3-template vertical pack", "Add setup call CTA", "Ask downloaders to pay for customization before building SaaS"]
        gtm = "Vertical SEO pages + local service communities + cold outreach to small clinics/services."
        commercial_score = 0.68
    elif any(w in q for w in ["invoice", "late fee", "payment", "estimate", "tax", "calculator"]):
        icp = "Freelancer / contractor / small business finance operator"
        pain = "They need quick, defensible calculations for invoices, fees, estimates, or payment reminders."
        pay_trigger = "Pays when calculation accuracy or professional output directly affects cash collection."
        wedge = "Calculator plus printable/exportable invoice/payment artifact, not just a generic calculator."
        business_type = "SEO calculator → affiliate/lead magnet → paid templates"
        commercial_mvp = "A calculator with export/print output and a paid bundle or affiliate CTA at the result step."
        revenue_path = "Calculator traffic → export/paywall CTA → paid bundle or accounting affiliate."
        pricing = "$9-$29 one-time bundle; affiliate CPA if accounting/payment intent appears."
        first_sale_test = ["Add paid export/template CTA", "Track calculate→export→checkout clicks", "Test affiliate CTA vs paid bundle CTA"]
        gtm = "SEO calculator pages + long-tail fee/tax/payment queries + finance template directories."
        commercial_score = 0.62
    elif any(w in q for w in ["compliance", "audit", "vendor", "training", "permit", "renewal"]):
        icp = "Operations / compliance owner in a small regulated business"
        pain = "They need to avoid missed deadlines, audits, renewals, or vendor compliance gaps."
        pay_trigger = "Pays when missed compliance creates financial, legal, or operational risk."
        wedge = "Deadline/checklist tracker for one narrow regulation or workflow, not a broad compliance platform."
        business_type = "leadgen + paid report/template → vertical micro-SaaS"
        commercial_mvp = "A checklist/tracker that produces an exportable compliance artifact and tests paid report/subscription intent."
        revenue_path = "Free checklist/tracker → paid compliance packet/report → leadgen or subscription workflow."
        pricing = "$49-$199 paid packet/report; $29-$99/mo tracker if recurring deadline pain is validated."
        first_sale_test = ["Sell one compliance checklist/report", "Gate export behind work email", "Interview users before building recurring software"]
        gtm = "Narrow compliance SEO + professional communities + partnerships with consultants."
        commercial_score = 0.72
    go_no_go = "Go" if commercial_score >= 0.68 else ("Watch" if commercial_score >= 0.58 else "No-Go")
    key_assumption = "Users will pay for a more specific, workflow-ready output rather than consuming generic free content."
    return {"type":"business", "business_type": business_type, "icp": icp, "pain": pain, "pay_trigger": pay_trigger, "wedge": wedge, "commercial_mvp": commercial_mvp, "revenue_path": revenue_path, "pricing": pricing, "gtm": gtm, "first_sale_test": first_sale_test, "commercial_score": commercial_score, "go_no_go": go_no_go, "key_assumption": key_assumption, "monetization": monetization_type}

def make_card(db: Session, keyword: models.Keyword) -> models.OpportunityCard:
    serp = db.query(models.SerpResult).filter_by(keyword_id=keyword.id).all() or run_serp(db, keyword)
    comps = analyze_competitors(db, keyword)
    socials = collect_social(db, keyword)
    gap = sum(s.weakness_score for s in serp[:10]) / max(1, len(serp[:10]))
    strong_count = sum(1 for s in serp if "strong_brand" in (s.gap_tags or ""))
    mismatch_count = sum(1 for s in serp if "query_mismatch" in (s.gap_tags or ""))
    relevant_count = max(0, len(serp) - mismatch_count)
    forum_count = sum(1 for s in serp if "forum_heavy" in (s.gap_tags or ""))
    demand = min(1.0, 0.30 + 0.06*relevant_count + 0.08*len(socials))
    comp = min(1.0, 0.35 + 0.1*len(comps) + 0.08*forum_count - 0.06*strong_count)
    mtype, mscore = monetization(keyword.query, keyword.intent)
    biz = business_profile(keyword.query, keyword.intent, mtype)
    commercial = float(biz.get("commercial_score", 0.55))
    total = round(100*(0.23*demand + 0.23*gap + 0.18*comp + 0.21*commercial + 0.15*mscore), 1)
    has_social = len(socials) > 0
    try:
        min_action_score = float(setting(db, "MIN_ACTION_SCORE") or "74")
    except Exception:
        min_action_score = 74.0
    require_social = (setting(db, "REQUIRE_SOCIAL_FOR_ACTION") or "true").lower() in {"1", "true", "yes", "on"}
    social_ok = has_social or not require_social
    verdict = "Action" if total >= min_action_score and strong_count <= 2 and gap >= .52 and social_ok and relevant_count >= 5 else ("Watch" if total >= 55 and relevant_count >= 3 else "Reject")
    evidence = [biz] + [{"type":"serp","url":s.url,"title":s.title,"tags":json.loads(s.gap_tags or "[]")} for s in serp[:5]] + [{"type":x.platform,"url":x.url,"title":x.title} for x in socials[:4]]
    risks=[]
    if strong_count>3: risks.append("SERP 强品牌过多，切入难度高")
    if len(socials)==0 and require_social: risks.append("缺少社媒痛点旁证")
    if mismatch_count >= max(2, len(serp)//2): risks.append("SERP 查询意图不匹配，搜索入口不可靠")
    if gap<.5: risks.append("SERP 缺口不明显")
    plan = f"商业目标：{biz['business_type']}。快速商业 MVP：{biz['commercial_mvp']} 商业化路径：{biz['revenue_path']} 定价：{biz['pricing']} 获客：{biz['gtm']} 第一笔钱测试：{' / '.join(biz['first_sale_test'])}。关键假设：{biz['key_assumption']}"
    card=models.OpportunityCard(keyword_id=keyword.id,title=f"{keyword.query} opportunity", verdict=verdict, score=total, demand_score=round(demand,2), serp_gap_score=round(gap,2), competitor_weakness_score=round(comp,2), mvp_score=commercial, monetization_score=mscore, monetization_type=mtype, mvp_plan=plan, evidence_json=json.dumps(evidence,ensure_ascii=False), risks=json.dumps(risks,ensure_ascii=False))
    db.add(card); keyword.score=total; keyword.status=verdict.lower(); db.commit(); db.refresh(card); return card

def daily_run(db: Session, limit=12, roots=None, use_four_find: bool | None = None, seeds: list[str] | None = None) -> models.RunHistory:
    # recover stale runs from previous crashes/restarts so dashboard does not stay "running" forever
    stale = db.query(models.RunHistory).filter(models.RunHistory.status == "running").all()
    for old in stale:
        old.status = "failed"
        old.summary = "stale running run recovered before new run"
        old.finished_at = datetime.utcnow()
    db.commit()
    run=models.RunHistory(kind="daily", status="running"); db.add(run); db.commit(); db.refresh(run)
    try:
        if use_four_find is None:
            use_four_find = (setting(db, "FOUR_FIND_AUTO_ENABLED") or "false").lower() in {"1", "true", "yes", "on"}
        if use_four_find:
            kws = discover_keywords_four_find(db, limit=limit, seeds=seeds)
            if len(kws) < limit:
                existing = {kw.query for kw in kws}
                for kw in discover_keywords(db, limit=limit, roots=roots):
                    if kw.query not in existing:
                        kws.append(kw)
                        existing.add(kw.query)
                    if len(kws) >= limit:
                        break
        else:
            kws=discover_keywords(db, limit=limit, roots=roots)
        cards=[]
        skipped=[]
        kws = [kw for kw in kws if kw.status not in {"rejected", "serp_reject", "rewrite_exhausted"}]
        total_kws = len(kws[:limit])
        for idx, kw in enumerate(kws[:limit], 1):
            run.summary=json.dumps({"phase":"running", "current": idx, "total": total_kws, "keyword": kw.query, "cards": len(cards)}, ensure_ascii=False)
            db.commit()
            serp, strategy_meta = run_serp_with_strategy(db, kw)
            admissible, gate = serp_admissibility(serp)
            if not admissible:
                mark_four_find_serp_reject(db, kw, gate)
                skipped.append({"keyword": kw.query, "serp_strategy": strategy_meta, **gate})
                continue
            cards.append(make_card(db, kw))
        rewrite_summary = None
        if (setting(db, "FOUR_FIND_REWRITE_ON_SERP_REJECT") or "false").lower() in {"1", "true", "yes", "on"} and skipped:
            try:
                rewrite_limit = int(setting(db, "FOUR_FIND_REWRITE_LIMIT") or "8")
            except Exception:
                rewrite_limit = 8
            rewrite_summary = recover_serp_rejects(db, limit=rewrite_limit)
            if rewrite_summary.get("cards"):
                recovered_cards = db.query(models.OpportunityCard).order_by(models.OpportunityCard.created_at.desc()).limit(int(rewrite_summary.get("cards") or 0)).all()
                cards.extend(recovered_cards)
        summary={
            "phase":"finished",
            "keywords":len(kws),
            "cards":len(cards),
            "action":sum(1 for c in cards if c.verdict=="Action"),
            "watch":sum(1 for c in cards if c.verdict=="Watch"),
            "reject":sum(1 for c in cards if c.verdict=="Reject"),
            "use_four_find": bool(use_four_find),
            "four_find_keywords": sum(1 for k in kws if k.source.startswith("four_find:")),
            "root_combo_keywords": sum(1 for k in kws if k.source == "root_combo"),
            "skipped_low_quality_serp": len(skipped),
            "skipped_examples": skipped[:5],
            "rewrite_recovery": rewrite_summary,
        }
        run.status="ok"; run.summary=json.dumps(summary, ensure_ascii=False); run.finished_at=datetime.utcnow()
    except Exception as e:
        run.status="failed"; run.summary=str(e); run.finished_at=datetime.utcnow()
    db.commit(); db.refresh(run); return run


def test_search_provider(db: Session) -> dict:
    endpoint = (searxng_endpoints(db) or [{"url": setting(db, "SEARXNG_URL").rstrip("/"), "api_token": setting(db, "SEARXNG_API_TOKEN"), "use_builtin_engines": not bool(setting(db, "SEARXNG_ENGINES")), "engines": setting(db, "SEARXNG_ENGINES")}])[0]
    base = endpoint["url"].rstrip("/")
    started = datetime.utcnow()
    providers = {"available": available_serp_providers(db), "searxng_urls": len(searxng_urls(db)), "brave_keys": len(rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")), "tavily_keys": len(rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY")), "brave_configured": bool(rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")), "tavily_configured": bool(rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY"))}
    try:
        headers = {"Accept": "application/json"}
        if endpoint.get("api_token"):
            headers["X-API-TOKEN"] = endpoint["api_token"]
        params={"q":"invoice calculator", "format":"json", "language":"en"}
        if not endpoint.get("use_builtin_engines", True) and endpoint.get("engines"):
            params["engines"] = endpoint["engines"]
        r = requests.get(f"{base}/search", params=params, headers=headers, timeout=12)
        elapsed_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
        r.raise_for_status()
        data = r.json()
        return {"ok": True, "url": base, "elapsed_ms": elapsed_ms, "result_count": len(data.get("results", [])), "sample": (data.get("results") or [{}])[0], "providers": providers}
    except Exception as e:
        return {"ok": False, "url": base, "error": str(e), "providers": providers}

def apply_feedback(db: Session, card: models.OpportunityCard, label: str, note: str = "") -> models.OpportunityCard:
    card.feedback_label = label
    card.feedback_note = note
    if label not in {"Action", "Watch", "Reject", "Block"}:
        db.commit(); db.refresh(card); return card
    kw = db.get(models.Keyword, card.keyword_id)
    roots = []
    if kw:
        try: roots = json.loads(kw.root_terms or "[]")
        except Exception: roots = []
        kw.status = label.lower()
        # Four-Find closed loop: feedback on generated cards should change the
        # next discovery cycle, not just the card label.
        if kw.source.startswith("four_find:"):
            good = label in {"Action", "Watch"}
            bad = label in {"Reject", "Block"}
            for seed in roots:
                exp = db.query(models.DiscoveryExpansion).filter_by(seed_keyword=seed, expanded_keyword=kw.query).first()
                if exp:
                    exp.score = max(0.0, min(1.0, (exp.score or 0.0) + (0.18 if good else -0.25)))
                    exp.status = "imported" if good else "rejected"
                ck = db.query(models.CompetitorKeyword).filter_by(competitor_domain=seed, discovered_keyword=kw.query).first()
                if ck:
                    ck.score = max(0.0, min(1.0, (ck.score or 0.0) + (0.18 if good else -0.25)))
                    ck.status = "imported" if good else "rejected"
                # Site→Site learning: if the keyword came from a competitor domain,
                # promote or reject related competitor-site edges as discovery seeds.
                if "." in seed:
                    for site in db.query(models.CompetitorSite).filter((models.CompetitorSite.seed_domain == seed) | (models.CompetitorSite.similar_domain == seed)).all():
                        site.score = max(0.0, min(1.0, (site.score or 0.0) + (0.12 if good else -0.2)))
                        site.status = "promoted" if good else "rejected"
            # Promote good Four-Find seeds into the auto seed list; bad seeds are
            # removed/blocked so the automatic loop learns from review.
            row = db.get(models.Setting, "FOUR_FIND_AUTO_SEEDS") or models.Setting(key="FOUR_FIND_AUTO_SEEDS", value="")
            seeds = [x.strip() for x in (row.value or "").split(",") if x.strip()]
            domain_row = db.get(models.Setting, "FOUR_FIND_AUTO_DOMAINS") or models.Setting(key="FOUR_FIND_AUTO_DOMAINS", value="")
            domains = [x.strip() for x in re.split(r"[\n,]+", (domain_row.value or "")) if x.strip()]
            if good:
                for seed in roots:
                    if seed and "." in seed and seed not in domains:
                        domains.append(seed)
                    elif seed and seed not in seeds:
                        seeds.append(seed)
            if bad:
                seeds = [s for s in seeds if s not in roots]
                domains = [d for d in domains if d not in roots]
            row.value = ",".join(seeds)
            row.secret = False
            db.merge(row)
            domain_row.value = "\n".join(domains)
            domain_row.secret = False
            db.merge(domain_row)
    delta = {"Action": 0.2, "Watch": 0.05, "Reject": -0.15, "Block": -0.5}.get(label, 0)
    for term in roots:
        root = db.query(models.Root).filter_by(term=term).first()
        if not root: continue
        root.weight = max(0.05, min(5.0, (root.weight or 1.0) + delta))
        if label == "Block":
            root.enabled = False
            blocked = [t.strip() for t in setting(db, "BLOCKED_TERMS").split(",") if t.strip()]
            if term not in blocked:
                blocked.append(term)
                row = db.get(models.Setting, "BLOCKED_TERMS") or models.Setting(key="BLOCKED_TERMS")
                row.value = ",".join(sorted(set(blocked)))
                row.secret = False
                db.merge(row)
    if kw and kw.source.startswith("four_find:") and label == "Block":
        blocked = [t.strip() for t in setting(db, "BLOCKED_TERMS").split(",") if t.strip()]
        blocked.append(kw.query)
        for term in roots:
            if term:
                blocked.append(term)
        row = db.get(models.Setting, "BLOCKED_TERMS") or models.Setting(key="BLOCKED_TERMS")
        row.value = ",".join(sorted(set(blocked)))
        row.secret = False
        db.merge(row)
    db.commit(); db.refresh(card); return card

def auto_status(db: Session) -> dict:
    last = db.query(models.RunHistory).order_by(models.RunHistory.started_at.desc()).first()
    enabled = (setting(db, "AUTO_RUN_ENABLED") or "false").lower() in {"1","true","yes","on"}
    try: interval = int(setting(db, "AUTO_RUN_INTERVAL_MINUTES") or "360")
    except Exception: interval = 360
    return {"enabled": enabled, "interval_minutes": interval, "last_run": None if not last else {"id": last.id, "status": last.status, "summary": json.loads(last.summary or "{}") if last.summary and last.summary.startswith("{") else last.summary, "started_at": last.started_at.isoformat(), "finished_at": last.finished_at.isoformat() if last.finished_at else None}}

def auto_due(db: Session) -> bool:
    st = auto_status(db)
    if not st["enabled"]: return False
    last = db.query(models.RunHistory).order_by(models.RunHistory.started_at.desc()).first()
    if not last or not last.finished_at: return True
    return (datetime.utcnow() - last.finished_at).total_seconds() >= st["interval_minutes"] * 60

def auto_tick(db: Session) -> dict:
    if not auto_due(db):
        return {"ran": False, "status": auto_status(db)}
    try: limit = int(setting(db, "AUTO_RUN_LIMIT") or "24")
    except Exception: limit = 24
    run = daily_run(db, limit=limit)
    export_latest_markdown(db)
    return {"ran": True, "run": {"id": run.id, "status": run.status, "summary": json.loads(run.summary or "{}") if run.summary and run.summary.startswith("{") else run.summary}}

def export_latest_markdown(db: Session) -> str:
    from pathlib import Path
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = db.query(models.OpportunityCard).order_by(models.OpportunityCard.score.desc()).limit(30).all()
    lines = ["# Demand Hunter Latest Cards", "", f"Generated: {datetime.utcnow().isoformat()}Z", ""]
    for c in cards:
        kw = db.get(models.Keyword, c.keyword_id)
        lines += [f"## {c.verdict} · {c.score} · {kw.query if kw else c.title}", "", f"- Monetization: {c.monetization_type}", f"- Demand: {c.demand_score}", f"- SERP Gap: {c.serp_gap_score}", f"- Competitor Weakness: {c.competitor_weakness_score}", f"- Commercial: {c.mvp_score}", "", "Commercialization:", c.mvp_plan, ""]
        risks = json.loads(c.risks or "[]")
        if risks:
            lines += ["Risks:"] + [f"- {r}" for r in risks] + [""]
        evidence = json.loads(c.evidence_json or "[]")[:6]
        if evidence:
            lines += ["Evidence:"] + [f"- [{e.get('type','web')}] {e.get('title','')} {e.get('url','')}" for e in evidence] + [""]
    path = out_dir / "demand_cards_latest.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
