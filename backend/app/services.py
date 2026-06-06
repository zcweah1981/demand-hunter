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
    "SEARXNG_API_TOKEN": "",
    "SEARXNG_ENGINES": "bing,wikipedia",
    "BRAVE_API_KEY": "",
    "TAVILY_API_KEY": "",
    "LLM_PROVIDER": "",
    "LLM_API_KEY": "",
    "AUTO_RUN_ENABLED": "true",
    "AUTO_RUN_INTERVAL_MINUTES": "360",
    "AUTO_RUN_LIMIT": "12",
    "MIN_ACTION_SCORE": "74",
    "REQUIRE_SOCIAL_FOR_ACTION": "false",
    "COLLECT_SOCIAL_EVIDENCE": "false",
    "BLOCKED_TERMS": "booking,best",
    "FOUR_FIND_AUTO_ENABLED": "true",
    "FOUR_FIND_AUTO_SEEDS": "invoice calculator,appointment template,compliance tracker",
    "FOUR_FIND_IMPORT_LIMIT": "12",
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
            db.add(models.Setting(key=k, value=default_value, secret=k.endswith("KEY") or k.endswith("TOKEN")))
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
    if seeds is None:
        raw = setting(db, "FOUR_FIND_AUTO_SEEDS") or ""
        seeds = [x.strip() for x in raw.split(",") if x.strip()]
    if not seeds:
        return []
    try:
        import_limit = int(setting(db, "FOUR_FIND_IMPORT_LIMIT") or str(limit))
    except Exception:
        import_limit = limit
    out: list[models.Keyword] = []
    seen: set[str] = set()
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

def searxng_search(db: Session, query: str, categories="general", limit=10) -> list[dict]:
    base = setting(db, "SEARXNG_URL").rstrip("/")
    if not base:
        return []
    headers = {"Accept": "application/json"}
    token = setting(db, "SEARXNG_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        params={"q": query, "format":"json", "categories":categories, "language":"en"}
        engines = setting(db, "SEARXNG_ENGINES")
        if engines: params["engines"] = engines
        r = requests.get(f"{base}/search", params=params, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])[:limit]
    except Exception as e:
        return [{"title":"SearXNG error", "url":"", "content":str(e), "engine":"error"}]

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

def run_serp(db: Session, keyword: models.Keyword) -> list[models.SerpResult]:
    db.query(models.SerpResult).filter_by(keyword_id=keyword.id).delete()
    results = searxng_search(db, keyword.query, limit=10)
    rows = []
    for i, item in enumerate(results, 1):
        tags, weakness = gap_tags_for(item, keyword.query)
        row = models.SerpResult(keyword_id=keyword.id, rank=i, title=item.get("title") or "", url=item.get("url") or "", snippet=item.get("content") or item.get("snippet") or "", domain=domain(item.get("url") or ""), gap_tags=json.dumps(tags), weakness_score=weakness)
        db.add(row); rows.append(row)
    db.commit()
    return rows

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
    relevant = len(top) - mismatch
    avg_gap = sum(s.weakness_score for s in top) / max(1, len(top))
    ok = relevant >= 5 and mismatch <= max(3, len(top)//2) and avg_gap >= 0.32
    return ok, {"relevant": relevant, "mismatch": mismatch, "strong": strong, "avg_gap": round(avg_gap, 3), "reason": "ok" if ok else "weak_or_mismatched_serp"}

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
    mvp = 0.8 if any(w in keyword.query for w in ["calculator","template","generator","tracker"]) else 0.62
    total = round(100*(0.25*demand + 0.25*gap + 0.2*comp + 0.15*mvp + 0.15*mscore), 1)
    has_social = len(socials) > 0
    try:
        min_action_score = float(setting(db, "MIN_ACTION_SCORE") or "74")
    except Exception:
        min_action_score = 74.0
    require_social = (setting(db, "REQUIRE_SOCIAL_FOR_ACTION") or "true").lower() in {"1", "true", "yes", "on"}
    social_ok = has_social or not require_social
    verdict = "Action" if total >= min_action_score and strong_count <= 2 and gap >= .52 and social_ok and relevant_count >= 5 else ("Watch" if total >= 55 and relevant_count >= 3 else "Reject")
    evidence = [{"type":"serp","url":s.url,"title":s.title,"tags":json.loads(s.gap_tags or "[]")} for s in serp[:5]] + [{"type":x.platform,"url":x.url,"title":x.title} for x in socials[:4]]
    risks=[]
    if strong_count>3: risks.append("SERP 强品牌过多，切入难度高")
    if len(socials)==0 and require_social: risks.append("缺少社媒痛点旁证")
    if mismatch_count >= max(2, len(serp)//2): risks.append("SERP 查询意图不匹配，搜索入口不可靠")
    if gap<.5: risks.append("SERP 缺口不明显")
    plan = f"围绕 `{keyword.query}` 做一个单页 MVP：输入关键业务参数，输出可下载结果/模板；首屏解释目标用户、3 个使用场景、FAQ，并用 SearXNG/SERP 证据继续扩展长尾词。"
    card=models.OpportunityCard(keyword_id=keyword.id,title=f"{keyword.query} opportunity", verdict=verdict, score=total, demand_score=round(demand,2), serp_gap_score=round(gap,2), competitor_weakness_score=round(comp,2), mvp_score=mvp, monetization_score=mscore, monetization_type=mtype, mvp_plan=plan, evidence_json=json.dumps(evidence,ensure_ascii=False), risks=json.dumps(risks,ensure_ascii=False))
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
        kws = [kw for kw in kws if kw.status != "rejected"]
        total_kws = len(kws[:limit])
        for idx, kw in enumerate(kws[:limit], 1):
            run.summary=json.dumps({"phase":"running", "current": idx, "total": total_kws, "keyword": kw.query, "cards": len(cards)}, ensure_ascii=False)
            db.commit()
            serp = run_serp(db, kw)
            admissible, gate = serp_admissibility(serp)
            if not admissible:
                kw.status = "serp_reject"
                skipped.append({"keyword": kw.query, **gate})
                db.commit()
                continue
            cards.append(make_card(db, kw))
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
        }
        run.status="ok"; run.summary=json.dumps(summary, ensure_ascii=False); run.finished_at=datetime.utcnow()
    except Exception as e:
        run.status="failed"; run.summary=str(e); run.finished_at=datetime.utcnow()
    db.commit(); db.refresh(run); return run


def test_search_provider(db: Session) -> dict:
    base = setting(db, "SEARXNG_URL").rstrip("/")
    started = datetime.utcnow()
    try:
        engines = setting(db, "SEARXNG_ENGINES") or "bing,wikipedia"
        r = requests.get(f"{base}/search", params={"q":"invoice calculator", "format":"json", "language":"en", "engines": engines}, timeout=12)
        elapsed_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
        r.raise_for_status()
        data = r.json()
        return {"ok": True, "url": base, "elapsed_ms": elapsed_ms, "result_count": len(data.get("results", [])), "sample": (data.get("results") or [{}])[0]}
    except Exception as e:
        return {"ok": False, "url": base, "error": str(e)}

def apply_feedback(db: Session, card: models.OpportunityCard, label: str, note: str = "") -> models.OpportunityCard:
    card.feedback_label = label
    card.feedback_note = note
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
            # Promote good Four-Find seeds into the auto seed list; bad seeds are
            # removed/blocked so the automatic loop learns from review.
            row = db.get(models.Setting, "FOUR_FIND_AUTO_SEEDS") or models.Setting(key="FOUR_FIND_AUTO_SEEDS", value="")
            seeds = [x.strip() for x in (row.value or "").split(",") if x.strip()]
            if good:
                for seed in roots:
                    if seed and seed not in seeds:
                        seeds.append(seed)
            if bad:
                seeds = [s for s in seeds if s not in roots]
            row.value = ",".join(seeds)
            row.secret = False
            db.merge(row)
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
        lines += [f"## {c.verdict} · {c.score} · {kw.query if kw else c.title}", "", f"- Monetization: {c.monetization_type}", f"- Demand: {c.demand_score}", f"- SERP Gap: {c.serp_gap_score}", f"- Competitor Weakness: {c.competitor_weakness_score}", f"- MVP: {c.mvp_score}", "", "MVP:", c.mvp_plan, ""]
        risks = json.loads(c.risks or "[]")
        if risks:
            lines += ["Risks:"] + [f"- {r}" for r in risks] + [""]
        evidence = json.loads(c.evidence_json or "[]")[:6]
        if evidence:
            lines += ["Evidence:"] + [f"- [{e.get('type','web')}] {e.get('title','')} {e.get('url','')}" for e in evidence] + [""]
    path = out_dir / "demand_cards_latest.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
