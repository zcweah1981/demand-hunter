from __future__ import annotations
import json, re, hashlib
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from . import models

BAD_KEYWORD_TERMS = {
    "login", "sign in", "signup", "get started", "our map", "contact", "support", "pricing",
    "city", "county", "california", "bernardino", "near me", "home", "official", "portal",
    "capterra", "g2", "trustradius", "spectrum", "facebook", "linkedin", "youtube",
    "dmv", "gov", "myuscis", "lavote", "apply", "make", "agency", "available", "office",
}
BAD_SINGLE_MODIFIERS = {
    "for", "and", "with", "from", "your", "their", "this", "that", "login", "city", "home",
    "page", "about", "contact", "support", "license", "portal", "map", "started",
}
GOOD_INTENT_TERMS = {
    "calculator", "template", "generator", "tracker", "dashboard", "checklist", "software",
    "tool", "automation", "workflow", "compliance", "invoice", "appointment", "schedule",
    "deadline", "clinic", "contractor", "rental", "small business", "management", "report",
}
COMMERCIAL_ICP_TERMS = {
    "clinic", "dental", "doctor", "patient", "salon", "contractor", "rental", "landlord",
    "freelancer", "small business", "vendor", "employee", "audit", "compliance", "permit",
    "renewal", "training", "client", "invoice", "payment", "tax",
}
COMMERCIAL_OUTPUT_TERMS = {
    "calculator", "template", "checklist", "tracker", "dashboard", "report", "packet",
    "form", "letter", "email", "policy", "spreadsheet", "generator", "estimate", "receipt",
}
PAY_TRIGGER_TERMS = {
    "late", "fee", "overdue", "deadline", "renewal", "audit", "risk", "penalty",
    "payment", "no show", "cancellation", "reschedule", "compliance", "tax",
}
GOOD_MODIFIERS = {
    "clinic", "dental", "salon", "doctor", "patient", "client", "contractor", "rental",
    "reminder", "cancellation", "reschedule", "intake", "form", "sms", "calendar",
    "workflow", "dashboard", "tracker", "checklist", "calculator", "software", "management",
    "deadline", "compliance", "invoice", "booking", "schedule", "scheduling", "policy", "report",
    "audit", "vendor", "employee", "training", "risk", "inspection", "renewal", "permit",
    "late", "fee", "payment", "tax", "estimate", "overdue", "receipt", "penalty", "cost",
}

BUSINESS_MODIFIER_SETS = {
    "appointment": [
        "clinic", "dental", "patient", "reminder", "cancellation", "reschedule",
        "intake", "sms", "calendar", "doctor", "salon", "client",
    ],
    "template": [
        "clinic", "patient", "reminder", "cancellation", "reschedule", "intake",
        "email", "sms", "form", "policy",
    ],
    "compliance": [
        "deadline", "audit", "vendor", "employee", "training", "policy", "risk",
        "inspection", "renewal", "permit", "report", "dashboard",
    ],
    "tracker": [
        "deadline", "dashboard", "workflow", "report", "management", "checklist",
        "audit", "vendor", "employee", "renewal",
    ],
    "invoice": [
        "late fee", "payment", "contractor", "rental", "small business", "reminder",
        "receipt", "tax", "estimate", "overdue", "freelancer", "landlord", "payment reminder",
    ],
    "calculator": [
        "late fee", "tax", "margin", "payment", "contractor", "rental", "estimate",
        "deadline", "penalty", "cost",
    ],
}

COMMERCIAL_QUERY_PATTERNS = {
    "appointment": [
        "appointment reminder template for clinic", "patient no show policy template",
        "appointment cancellation fee template", "dental appointment reminder sms template",
    ],
    "invoice": [
        "overdue invoice payment reminder template", "invoice late fee calculator for small business",
        "contractor invoice estimate template", "rental late fee notice template",
    ],
    "compliance": [
        "vendor compliance checklist template", "employee training compliance tracker",
        "permit renewal deadline tracker", "audit readiness checklist template",
    ],
}

def business_modifier_variants(seed_keyword: str, limit: int = 12) -> list[str]:
    """Generate task/vertical long-tail candidates from seed semantics.

    This supplements SERP-title extraction. SERP titles are noisy; business modifiers
    keep Four-Find anchored in real user tasks.
    """
    seed = re.sub(r"\s+", " ", seed_keyword.lower()).strip()
    seed_words = set(re.findall(r"[a-z0-9]+", seed))
    modifiers: list[str] = []
    out: list[str] = []
    seen: set[str] = set()
    for key, values in BUSINESS_MODIFIER_SETS.items():
        if key in seed_words:
            modifiers.extend(values)
            for pattern in COMMERCIAL_QUERY_PATTERNS.get(key, []):
                if pattern not in seen:
                    seen.add(pattern)
                    out.append(pattern)
                    if len(out) >= limit:
                        return out
    for modifier in modifiers:
        candidates = [f"{modifier} {seed}"]
        if "template" in seed_words and modifier not in seed:
            candidates.append(f"{modifier} template")
        if "tracker" in seed_words and modifier not in seed:
            candidates.append(f"{modifier} tracker")
        for candidate in candidates:
            candidate = re.sub(r"\s+", " ", candidate).strip()
            if candidate != seed and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
            if len(out) >= limit:
                return out
    return out

# --- helpers ---

def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""

def keyword_quality_score(seed: str, keyword: str, source_domain: str = "") -> tuple[float, list[str]]:
    """Heuristic pre-import quality score for Four-Find candidates.

    The goal is not to predict opportunity score; it only blocks obvious SERP noise
    before it wastes SERP/card budget.
    """
    kw = re.sub(r"\s+", " ", (keyword or "").lower()).strip()
    seed_l = (seed or "").lower().strip()
    reasons: list[str] = []
    score = 0.55

    if len(kw) < 8 or len(kw) > 90:
        score -= 0.25; reasons.append("bad_length")
    if kw == seed_l:
        score -= 0.2; reasons.append("same_as_seed")
    if seed_l and seed_l.replace(" ", "") in kw.replace(" ", "") and kw.replace(" ", "").count(seed_l.replace(" ", "")) > 1:
        score -= 0.45; reasons.append("seed_repeated_or_brand_echo")
    if any(term in kw for term in BAD_KEYWORD_TERMS):
        score -= 0.45; reasons.append("blocked_noise_term")
    words = re.findall(r"[a-z0-9]+", kw)
    if len(words) < 2:
        score -= 0.3; reasons.append("too_short_phrase")
    if words and words[-1] in BAD_SINGLE_MODIFIERS:
        score -= 0.25; reasons.append("bad_modifier")
    seed_words = set(re.findall(r"[a-z0-9]+", seed_l))
    keyword_words = set(words)
    added_words = keyword_words - seed_words

    if any(term in kw for term in GOOD_INTENT_TERMS):
        score += 0.18; reasons.append("good_intent_term")
    commercial_hits = 0
    if any(term in kw for term in COMMERCIAL_ICP_TERMS):
        commercial_hits += 1; score += 0.12; reasons.append("commercial_icp")
    if any(term in kw for term in COMMERCIAL_OUTPUT_TERMS):
        commercial_hits += 1; score += 0.10; reasons.append("commercial_output")
    if any(term in kw for term in PAY_TRIGGER_TERMS):
        commercial_hits += 1; score += 0.14; reasons.append("pay_trigger")
    if commercial_hits == 0:
        score -= 0.18; reasons.append("no_commercial_signal")
    if seed_l and len(set(seed_l.split()) & set(words)) >= max(1, min(2, len(seed_l.split()))):
        score += 0.08; reasons.append("seed_overlap")
    if seed_words and added_words and not (added_words & GOOD_MODIFIERS):
        score -= 0.38; reasons.append("weak_added_modifier")
    if seed_words and len(added_words) == 1 and not (added_words & GOOD_MODIFIERS):
        score -= 0.22; reasons.append("single_noise_modifier")
    if source_domain and any(d in source_domain for d in ("capterra.com", "g2.com", "spectrum.com", "facebook.com", "linkedin.com")):
        score -= 0.25; reasons.append("weak_source_domain")

    return max(0.0, min(1.0, round(score, 3))), reasons

def candidate_is_importable(seed: str, keyword: str, source_domain: str = "") -> bool:
    score, reasons = keyword_quality_score(seed, keyword, source_domain)
    return score >= 0.68 and "blocked_noise_term" not in reasons and "seed_repeated_or_brand_echo" not in reasons and "weak_added_modifier" not in reasons and "no_commercial_signal" not in reasons

# --- 1. 词找词 (Keyword → Keyword) ---

def expand_by_suggest(db: Session, seed_keyword: str, searxng_search_fn, limit=10) -> list[models.DiscoveryExpansion]:
    """
    Use SearXNG search to find related searches.
    Also extract modifiers from SERP results.
    """
    results = []

    # Method 0: business/task modifiers. This prevents Four-Find from depending
    # entirely on noisy SERP titles such as DMV/gov/login pages.
    existing = set()
    for expanded in business_modifier_variants(seed_keyword, limit=limit):
        existing.add(expanded)
        row = db.query(models.DiscoveryExpansion).filter_by(
            seed_keyword=seed_keyword, expanded_keyword=expanded
        ).first()
        if not row:
            qscore, qreasons = keyword_quality_score(seed_keyword, expanded)
            row = models.DiscoveryExpansion(
                seed_keyword=seed_keyword,
                expanded_keyword=expanded,
                expansion_type="business_modifier",
                score=qscore,
                status="new" if candidate_is_importable(seed_keyword, expanded) else "rejected",
            )
            db.add(row)
            results.append(row)

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
    for word in sorted(title_words)[:limit]:
        expanded = f"{seed_keyword} {word}"
        if expanded not in existing:
            existing.add(expanded)
            row = db.query(models.DiscoveryExpansion).filter_by(
                seed_keyword=seed_keyword, expanded_keyword=expanded
            ).first()
            if not row:
                qscore, qreasons = keyword_quality_score(seed_keyword, expanded)
                row = models.DiscoveryExpansion(
                    seed_keyword=seed_keyword,
                    expanded_keyword=expanded,
                    expansion_type="modifier",
                    score=qscore,
                    status="new" if candidate_is_importable(seed_keyword, expanded) else "rejected",
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
                        source = domain(r.get("url", ""))
                        qscore, qreasons = keyword_quality_score(seed_keyword, expanded, source)
                        row = models.DiscoveryExpansion(
                            seed_keyword=seed_keyword,
                            expanded_keyword=expanded,
                            expansion_type="related",
                            source_domain=source,
                            score=qscore,
                            status="new" if candidate_is_importable(seed_keyword, expanded, source) else "rejected",
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
                        source = domain(r.get("url", ""))
                        qscore, qreasons = keyword_quality_score(seed_keyword, kw, source)
                        row = models.DiscoveryExpansion(
                            seed_keyword=seed_keyword,
                            expanded_keyword=kw,
                            expansion_type="related",
                            source_domain=source,
                            score=qscore,
                            status="new" if candidate_is_importable(seed_keyword, kw, source) else "rejected",
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
            qscore, qreasons = keyword_quality_score(competitor_domain, kw, competitor_domain)
            row = models.CompetitorKeyword(
                competitor_domain=competitor_domain,
                discovered_keyword=kw,
                source="title",
                source_url=url,
                score=qscore,
                status="new" if candidate_is_importable(competitor_domain, kw, competitor_domain) else "rejected",
            )
            db.add(row)
            results.append(row)

        # Also extract URL path keywords
        path_kw = _url_to_keyword(url, competitor_domain)
        if path_kw and path_kw not in existing:
            existing.add(path_kw)
            qscore, qreasons = keyword_quality_score(competitor_domain, path_kw, competitor_domain)
            row = models.CompetitorKeyword(
                competitor_domain=competitor_domain,
                discovered_keyword=path_kw,
                source="url_path",
                source_url=url,
                score=qscore,
                status="new" if candidate_is_importable(competitor_domain, path_kw, competitor_domain) else "rejected",
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
                qscore, qreasons = keyword_quality_score(competitor_domain, kw, competitor_domain)
                row = models.CompetitorKeyword(
                    competitor_domain=competitor_domain,
                    discovered_keyword=kw,
                    source="brand_search",
                    source_url=r.get("url", ""),
                    score=qscore,
                    status="new" if candidate_is_importable(competitor_domain, kw, competitor_domain) else "rejected",
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
        # Close the Site→Site→Keyword loop: similar sites are not just shown in
        # the UI; they become reverse-keyword sources automatically.
        if depth > 1:
            for sim in sims[:2]:
                sim_cks = find_keywords_from_site(db, sim.similar_domain, searxng_search_fn, limit=4)
                summary["competitor_keywords"].extend([{"domain": sim.similar_domain, "keyword": ck.discovered_keyword} for ck in sim_cks])

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

    q = db.query(models.DiscoveryExpansion).filter(models.DiscoveryExpansion.status == "new", models.DiscoveryExpansion.score >= 0.62)
    if seed_keyword:
        q = q.filter(models.DiscoveryExpansion.seed_keyword == seed_keyword)
    expansions = q.order_by(models.DiscoveryExpansion.score.desc(), models.DiscoveryExpansion.created_at.desc()).limit(limit).all()
    for expansion in expansions:
        if expansion.expanded_keyword in seen or not candidate_is_importable(expansion.seed_keyword, expansion.expanded_keyword, expansion.source_domain):
            expansion.status = "rejected"
            db.commit()
            continue
        kw = import_expansion_to_keywords(db, expansion.id)
        if kw:
            seen.add(kw.query)
            imported.append(kw)
        if len(imported) >= limit:
            return imported

    remaining = max(0, limit - len(imported))
    if remaining:
        cq = db.query(models.CompetitorKeyword).filter(models.CompetitorKeyword.status == "new", models.CompetitorKeyword.score >= 0.62)
        competitor_keywords = cq.order_by(models.CompetitorKeyword.score.desc(), models.CompetitorKeyword.created_at.desc()).limit(remaining).all()
        for ck in competitor_keywords:
            if ck.discovered_keyword in seen or not candidate_is_importable(ck.competitor_domain, ck.discovered_keyword, ck.competitor_domain):
                ck.status = "rejected"
                db.commit()
                continue
            kw = import_competitor_keyword(db, ck.id)
            if kw:
                seen.add(kw.query)
                imported.append(kw)

    return imported

def prune_low_quality_discoveries(db: Session) -> dict:
    """Re-score existing discoveries and reject obvious noise before import/card generation."""
    pruned_expansions = 0
    pruned_competitor_keywords = 0
    updated_keywords = 0

    for e in db.query(models.DiscoveryExpansion).all():
        qscore, reasons = keyword_quality_score(e.seed_keyword, e.expanded_keyword, e.source_domain)
        e.score = qscore
        if not candidate_is_importable(e.seed_keyword, e.expanded_keyword, e.source_domain):
            if e.status != "rejected":
                pruned_expansions += 1
            e.status = "rejected"
            kw = db.query(models.Keyword).filter_by(query=e.expanded_keyword).first()
            if kw and kw.source.startswith("four_find:") and kw.status not in {"watch", "action"}:
                kw.status = "rejected"
                updated_keywords += 1

    for ck in db.query(models.CompetitorKeyword).all():
        qscore, reasons = keyword_quality_score(ck.competitor_domain, ck.discovered_keyword, ck.competitor_domain)
        ck.score = qscore
        if not candidate_is_importable(ck.competitor_domain, ck.discovered_keyword, ck.competitor_domain):
            if ck.status != "rejected":
                pruned_competitor_keywords += 1
            ck.status = "rejected"
            kw = db.query(models.Keyword).filter_by(query=ck.discovered_keyword).first()
            if kw and kw.source.startswith("four_find:") and kw.status not in {"watch", "action"}:
                kw.status = "rejected"
                updated_keywords += 1

    db.commit()
    return {"pruned_expansions": pruned_expansions, "pruned_competitor_keywords": pruned_competitor_keywords, "updated_keywords": updated_keywords}

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
        "similar_site_status": count_by(similar_sites, "status"),
        "card_verdicts": verdicts,
        "card_feedback": feedback,
        "keyword_sources": sources,
        "seed_scores": sorted(seed_scores.values(), key=lambda x: (x["imported"], x["avg_score"]), reverse=True)[:20],
        "top_competitor_domains": sorted(({"domain": k, "keywords": v} for k, v in domains.items()), key=lambda x: x["keywords"], reverse=True)[:20],
    }
