from __future__ import annotations
import json, re, hashlib
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from . import models

# --- helpers ---

def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""

# --- 1. 词找词 (Keyword → Keyword) ---

def expand_by_suggest(db: Session, seed_keyword: str, searxng_search_fn, limit=10) -> list[models.DiscoveryExpansion]:
    """
    Use SearXNG search to find related searches.
    Also extract modifiers from SERP results.
    """
    results = []

    # Method 1: Search the seed keyword and extract modifier patterns from titles
    serp_results = searxng_search_fn(db, seed_keyword, limit=10)
    title_words = set()
    for r in serp_results:
        if (r.get("engine") or "") == "error":
            continue
        title = (r.get("title") or "").lower()
        words = re.findall(r"[a-z]{3,}", title)
        for w in words:
            if w not in seed_keyword.lower() and w not in {"best", "free", "online", "the", "your", "how", "what", "with", "from"}:
                title_words.add(w)

    # Create expanded keywords by appending modifiers
    existing = set()
    for word in sorted(title_words)[:limit]:
        expanded = f"{seed_keyword} {word}"
        if expanded not in existing:
            existing.add(expanded)
            row = db.query(models.DiscoveryExpansion).filter_by(
                seed_keyword=seed_keyword, expanded_keyword=expanded
            ).first()
            if not row:
                row = models.DiscoveryExpansion(
                    seed_keyword=seed_keyword,
                    expanded_keyword=expanded,
                    expansion_type="modifier",
                    score=0.5,
                )
                db.add(row)
                results.append(row)

    # Method 2: Search "related to {seed}" pattern
    alt_query = f"related to {seed_keyword}"
    alt_results = searxng_search_fn(db, alt_query, limit=5)
    for r in alt_results:
        if (r.get("engine") or "") == "error":
            continue
        title = (r.get("title") or "").lower()
        # Extract phrases like "X vs Y" or "alternatives to X"
        vs_match = re.findall(r"(?:vs?\.?|or|and)\s+([a-z][a-z\s]{2,30})", title)
        for match in vs_match:
            cleaned = match.strip()
            if cleaned and cleaned not in seed_keyword.lower() and len(cleaned) > 3:
                expanded = cleaned
                if expanded not in existing:
                    existing.add(expanded)
                    row = db.query(models.DiscoveryExpansion).filter_by(
                        seed_keyword=seed_keyword, expanded_keyword=expanded
                    ).first()
                    if not row:
                        row = models.DiscoveryExpansion(
                            seed_keyword=seed_keyword,
                            expanded_keyword=expanded,
                            expansion_type="related",
                            source_domain=domain(r.get("url", "")),
                            score=0.6,
                        )
                        db.add(row)
                        results.append(row)

    db.commit()
    return results

def expand_by_related(db: Session, seed_keyword: str, searxng_search_fn, limit=8) -> list[models.DiscoveryExpansion]:
    """
    Search for patterns like "vs", "alternative", "compared" to find related keywords.
    """
    results = []
    queries = [f"{seed_keyword} vs", f"{seed_keyword} alternative", f"{seed_keyword} compared"]
    existing_keywords = set(r.expanded_keyword for r in db.query(models.DiscoveryExpansion).filter_by(seed_keyword=seed_keyword).all())

    for q in queries:
        serp = searxng_search_fn(db, q, limit=5)
        for r in serp:
            if (r.get("engine") or "") == "error":
                continue
            title = (r.get("title") or "")
            # Extract "X vs Y" patterns
            parts = re.findall(r"(?:vs?\.?|versus)\s+([A-Za-z][A-Za-z\s-]{2,40})", title, re.IGNORECASE)
            for p in parts:
                kw = p.strip().lower()
                if kw and kw not in existing_keywords and kw not in seed_keyword.lower():
                    existing_keywords.add(kw)
                    row = db.query(models.DiscoveryExpansion).filter_by(
                        seed_keyword=seed_keyword, expanded_keyword=kw
                    ).first()
                    if not row:
                        row = models.DiscoveryExpansion(
                            seed_keyword=seed_keyword,
                            expanded_keyword=kw,
                            expansion_type="related",
                            source_domain=domain(r.get("url", "")),
                            score=0.7,
                        )
                        db.add(row)
                        results.append(row)
                        if len(results) >= limit:
                            db.commit()
                            return results

    db.commit()
    return results

# --- 2. 词找站 (Keyword → Site) ---

def find_sites_from_keyword(db: Session, keyword: str, searxng_search_fn, limit=10) -> list[dict]:
    """
    Search a keyword and extract the top domains/sites from SERP.
    Classify each site by type.
    """
    serp = searxng_search_fn(db, keyword, limit=limit)
    sites = []
    seen_domains = set()
    for r in serp:
        if (r.get("engine") or "") == "error":
            continue
        d = domain(r.get("url", ""))
        if not d or d in seen_domains:
            continue
        seen_domains.add(d)

        # Classify site type
        site_type = _classify_site(d, r.get("title", ""), r.get("content") or r.get("snippet", ""))

        sites.append({
            "domain": d,
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "snippet": (r.get("content") or r.get("snippet", ""))[:200],
            "site_type": site_type,
            "is_competitor": site_type in ("tool", "saas", "marketplace"),
            "is_weak": any(w in (r.get("title", "") + r.get("url", "")).lower() for w in ("free", "blog", "template", "pdf", "github")),
        })

    return sites

FORUM_DOMAINS_TUPLE = ("reddit.com", "news.ycombinator.com", "stackoverflow.com", "quora.com")
STRONG_DOMAINS_TUPLE = ("google.com", "microsoft.com", "adobe.com", "shopify.com", "intuit.com", "hubspot.com", "salesforce.com", "wikipedia.org", "amazon.com")

def _classify_site(domain: str, title: str, snippet: str) -> str:
    text = (domain + " " + title + " " + snippet).lower()
    if any(d in domain for d in FORUM_DOMAINS_TUPLE):
        return "forum"
    if any(d in domain for d in STRONG_DOMAINS_TUPLE):
        return "strong_brand"
    if any(w in text for w in ("calculator", "generator", "converter", "checker", "editor", "tracker")):
        return "tool"
    if any(w in text for w in ("pricing", "subscription", "sign up", "dashboard", "saas")):
        return "saas"
    if any(w in text for w in ("buy", "shop", "store", "marketplace", "product")):
        return "marketplace"
    if any(w in text for w in ("blog", "guide", "article", "tutorial", "how to")):
        return "content"
    if any(w in text for w in ("directory", "list", "top 10", "best")):
        return "directory"
    if "youtube.com" in domain or "vimeo.com" in domain:
        return "video"
    return "other"

# --- 3. 站找词 (Site → Keyword) ---

def find_keywords_from_site(db: Session, competitor_domain: str, searxng_search_fn, limit=15) -> list[models.CompetitorKeyword]:
    """
    Reverse-discover keywords from a competitor domain.
    Methods:
    1. site:domain search → extract page titles → convert to keywords
    2. "domain" keyword search → find what keywords they rank for
    """
    results = []
    existing = set(r.discovered_keyword for r in db.query(models.CompetitorKeyword).filter_by(competitor_domain=competitor_domain).all())

    # Method 1: site:domain search
    site_query = f"site:{competitor_domain}"
    serp = searxng_search_fn(db, site_query, limit=limit)
    for r in serp:
        if (r.get("engine") or "") == "error":
            continue
        title = (r.get("title") or "").strip()
        url = r.get("url") or ""
        if not title:
            continue
        # Convert page title to keyword
        kw = _title_to_keyword(title)
        if kw and kw not in existing:
            existing.add(kw)
            row = models.CompetitorKeyword(
                competitor_domain=competitor_domain,
                discovered_keyword=kw,
                source="title",
                source_url=url,
                score=0.6,
            )
            db.add(row)
            results.append(row)

        # Also extract URL path keywords
        path_kw = _url_to_keyword(url, competitor_domain)
        if path_kw and path_kw not in existing:
            existing.add(path_kw)
            row = models.CompetitorKeyword(
                competitor_domain=competitor_domain,
                discovered_keyword=path_kw,
                source="url_path",
                source_url=url,
                score=0.5,
            )
            db.add(row)
            results.append(row)

    # Method 2: search the domain name itself to find what they're known for
    brand_query = competitor_domain.split(".")[0]
    brand_serp = searxng_search_fn(db, f'"{brand_query}"', limit=5)
    for r in brand_serp:
        if (r.get("engine") or "") == "error":
            continue
        title = (r.get("title") or "").lower()
        # Extract descriptor phrases
        parts = re.findall(r"(?:is a|with|for|to)\s+([a-z][a-z\s]{3,40})", title)
        for p in parts:
            kw = p.strip()
            if kw and kw not in existing and len(kw) > 5:
                existing.add(kw)
                row = models.CompetitorKeyword(
                    competitor_domain=competitor_domain,
                    discovered_keyword=kw,
                    source="brand_search",
                    source_url=r.get("url", ""),
                    score=0.4,
                )
                db.add(row)
                results.append(row)

    db.commit()
    return results

def _title_to_keyword(title: str) -> str:
    """Convert a page title to a search keyword."""
    # Remove common suffixes (brand names after | or - )
    clean = re.split(r"\s*[|\-–]\s*", title)[0]
    # Remove common prefixes
    clean = re.sub(r"^(best|top \d+|free)\s+", "", clean, flags=re.IGNORECASE)
    clean = clean.strip().lower()
    # Keep only if reasonable length
    if 5 <= len(clean) <= 80:
        return clean
    return ""

def _url_to_keyword(url: str, base_domain: str) -> str:
    """Extract keyword from URL path."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path or path in ("", "home", "index"):
            return ""
        # Take the last meaningful path segment
        segments = [s for s in path.split("/") if s and not s.isdigit() and len(s) > 2]
        if not segments:
            return ""
        # Clean and join
        last = segments[-1].replace("-", " ").replace("_", " ").replace(".html", "").strip()
        if 5 <= len(last) <= 60:
            return last
        return ""
    except Exception:
        return ""

# --- 4. 站找站 (Site → Site) ---

def find_similar_sites(db: Session, seed_domain: str, searxng_search_fn, limit=10) -> list[models.CompetitorSite]:
    """
    Find sites similar to a competitor domain.
    Methods:
    1. "alternative to {domain}" search
    2. "sites like {domain}" search
    3. "vs {domain}" search
    """
    results = []
    existing = set(r.similar_domain for r in db.query(models.CompetitorSite).filter_by(seed_domain=seed_domain).all())
    brand = seed_domain.split(".")[0]

    queries = [
        f"alternative to {brand}",
        f"sites like {seed_domain}",
        f"{brand} vs",
        f"best {brand} alternatives",
    ]

    for q in queries:
        serp = searxng_search_fn(db, q, limit=4)
        for r in serp:
            if (r.get("engine") or "") == "error":
                continue
            d = domain(r.get("url", ""))
            if not d or d == seed_domain or d in existing:
                continue
            # Skip generic sites
            if any(s in d for s in ("google.com", "facebook.com", "twitter.com", "x.com", "youtube.com", "wikipedia.org", "reddit.com", "linkedin.com")):
                continue
            existing.add(d)
            row = db.query(models.CompetitorSite).filter_by(
                seed_domain=seed_domain, similar_domain=d
            ).first()
            if not row:
                row = models.CompetitorSite(
                    seed_domain=seed_domain,
                    similar_domain=d,
                    discovery_method="alternative_to",
                    source_url=r.get("url", ""),
                    title=r.get("title", ""),
                    score=0.6,
                )
                db.add(row)
                results.append(row)
                if len(results) >= limit:
                    db.commit()
                    return results

    db.commit()
    return results

# --- Full Four-Find Pipeline ---

def run_four_find(db: Session, seed_keyword: str, searxng_search_fn, depth=2) -> dict:
    """
    Run the complete four-find pipeline for a seed keyword.

    Steps:
    1. 词找词: Expand seed keyword → more keywords
    2. 词找站: Search seed → find top sites + classify
    3. 站找词: For each competitor site → reverse discover keywords
    4. 站找站: For each competitor site → find similar sites

    Returns summary dict.
    """
    summary = {
        "seed": seed_keyword,
        "expanded_keywords": [],
        "sites": [],
        "competitor_keywords": [],
        "similar_sites": [],
    }

    # Step 1: 词找词
    expansions = expand_by_suggest(db, seed_keyword, searxng_search_fn)
    related = expand_by_related(db, seed_keyword, searxng_search_fn)
    all_expansions = expansions + related
    summary["expanded_keywords"] = [e.expanded_keyword for e in all_expansions]

    # Step 2: 词找站
    sites = find_sites_from_keyword(db, seed_keyword, searxng_search_fn)
    summary["sites"] = sites

    # Step 3: 站找词 (for top competitor sites)
    competitor_domains = [s["domain"] for s in sites if s.get("is_competitor") or s.get("site_type") in ("tool", "saas", "content", "directory")][:depth]
    for cd in competitor_domains:
        cks = find_keywords_from_site(db, cd, searxng_search_fn)
        summary["competitor_keywords"].extend([{"domain": cd, "keyword": ck.discovered_keyword} for ck in cks])

    # Step 4: 站找站 (for top competitor sites)
    for cd in competitor_domains:
        sims = find_similar_sites(db, cd, searxng_search_fn)
        summary["similar_sites"].extend([{"from": cd, "domain": s.similar_domain, "title": s.title} for s in sims])

    return summary

# --- Import discovered keywords into main keyword table ---

def import_expansion_to_keywords(db: Session, expansion_id: int) -> models.Keyword | None:
    """Import a discovery expansion into the main keyword table."""
    expansion = db.get(models.DiscoveryExpansion, expansion_id)
    if not expansion:
        return None

    existing = db.query(models.Keyword).filter_by(query=expansion.expanded_keyword).first()
    if existing:
        expansion.status = "imported"
        db.commit()
        return existing

    kw = models.Keyword(
        query=expansion.expanded_keyword,
        source=f"four_find:{expansion.expansion_type}",
        root_terms=json.dumps([expansion.seed_keyword]),
        intent="search_demand",
    )
    db.add(kw)
    expansion.status = "imported"
    db.commit()
    db.refresh(kw)
    return kw

def import_competitor_keyword(db: Session, ck_id: int) -> models.Keyword | None:
    """Import a competitor keyword into the main keyword table."""
    ck = db.get(models.CompetitorKeyword, ck_id)
    if not ck:
        return None

    existing = db.query(models.Keyword).filter_by(query=ck.discovered_keyword).first()
    if existing:
        ck.status = "imported"
        db.commit()
        return existing

    kw = models.Keyword(
        query=ck.discovered_keyword,
        source=f"four_find:site_to_keyword",
        root_terms=json.dumps([ck.competitor_domain]),
    )
    db.add(kw)
    ck.status = "imported"
    db.commit()
    db.refresh(kw)
    return kw

def import_discovered_keywords(db: Session, seed_keyword: str | None = None, limit: int = 12) -> list[models.Keyword]:
    """Import high-scoring Four-Find keyword discoveries into the main Keyword table.

    This is intentionally an API/service capability, not a script step. It lets the
    web UI, daily runner, and auto worker all use the same persisted discovery path.
    """
    imported: list[models.Keyword] = []
    seen: set[str] = set()

    q = db.query(models.DiscoveryExpansion).filter(models.DiscoveryExpansion.status == "new")
    if seed_keyword:
        q = q.filter(models.DiscoveryExpansion.seed_keyword == seed_keyword)
    expansions = q.order_by(models.DiscoveryExpansion.score.desc(), models.DiscoveryExpansion.created_at.desc()).limit(limit).all()
    for expansion in expansions:
        if expansion.expanded_keyword in seen:
            continue
        kw = import_expansion_to_keywords(db, expansion.id)
        if kw:
            seen.add(kw.query)
            imported.append(kw)
        if len(imported) >= limit:
            return imported

    remaining = max(0, limit - len(imported))
    if remaining:
        cq = db.query(models.CompetitorKeyword).filter(models.CompetitorKeyword.status == "new")
        competitor_keywords = cq.order_by(models.CompetitorKeyword.score.desc(), models.CompetitorKeyword.created_at.desc()).limit(remaining).all()
        for ck in competitor_keywords:
            if ck.discovered_keyword in seen:
                continue
            kw = import_competitor_keyword(db, ck.id)
            if kw:
                seen.add(kw.query)
                imported.append(kw)

    return imported

def run_four_find_and_import(db: Session, seed_keyword: str, searxng_search_fn, depth=2, import_limit=12) -> dict:
    """Run the complete Four-Find pipeline and import discovered keywords via service/API logic."""
    summary = run_four_find(db, seed_keyword, searxng_search_fn, depth=depth)
    imported = import_discovered_keywords(db, seed_keyword=seed_keyword, limit=import_limit)
    summary["imported_keywords"] = [{"id": kw.id, "query": kw.query, "source": kw.source} for kw in imported]
    return summary

def discovery_loop_status(db: Session) -> dict:
    """Summarize the Four-Find closed loop: discovery -> import -> card -> feedback."""
    expansions = db.query(models.DiscoveryExpansion).all()
    competitor_keywords = db.query(models.CompetitorKeyword).all()
    similar_sites = db.query(models.CompetitorSite).all()
    keywords = db.query(models.Keyword).filter(models.Keyword.source.like("four_find:%")).all()
    keyword_ids = [k.id for k in keywords]
    cards = db.query(models.OpportunityCard).filter(models.OpportunityCard.keyword_id.in_(keyword_ids)).all() if keyword_ids else []

    def count_by(rows, attr):
        out: dict[str, int] = {}
        for row in rows:
            key = getattr(row, attr, "") or "unknown"
            out[key] = out.get(key, 0) + 1
        return out

    seed_scores: dict[str, dict] = {}
    for e in expansions:
        s = seed_scores.setdefault(e.seed_keyword, {"seed": e.seed_keyword, "expanded": 0, "imported": 0, "rejected": 0, "avg_score": 0.0})
        s["expanded"] += 1
        s["avg_score"] += e.score or 0
        if e.status == "imported": s["imported"] += 1
        if e.status == "rejected": s["rejected"] += 1
    for s in seed_scores.values():
        s["avg_score"] = round(s["avg_score"] / max(1, s["expanded"]), 3)

    verdicts = count_by(cards, "verdict")
    feedback = count_by(cards, "feedback_label")
    sources = count_by(keywords, "source")
    domains = count_by(competitor_keywords, "competitor_domain")

    return {
        "funnel": {
            "expansions": len(expansions),
            "competitor_keywords": len(competitor_keywords),
            "similar_sites": len(similar_sites),
            "imported_keywords": len(keywords),
            "cards": len(cards),
            "reviewed_cards": sum(1 for c in cards if c.feedback_label),
        },
        "expansion_status": count_by(expansions, "status"),
        "competitor_keyword_status": count_by(competitor_keywords, "status"),
        "card_verdicts": verdicts,
        "card_feedback": feedback,
        "keyword_sources": sources,
        "seed_scores": sorted(seed_scores.values(), key=lambda x: (x["imported"], x["avg_score"]), reverse=True)[:20],
        "top_competitor_domains": sorted(({"domain": k, "keywords": v} for k, v in domains.items()), key=lambda x: x["keywords"], reverse=True)[:20],
    }
