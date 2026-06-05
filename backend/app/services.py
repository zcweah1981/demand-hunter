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
    "BRAVE_API_KEY": "",
    "TAVILY_API_KEY": "",
    "LLM_PROVIDER": "",
    "LLM_API_KEY": "",
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
    root_rows = [r for r in root_rows if r.term.lower() not in BLOCKED_AMBIGUOUS_ROOTS]
    for a,b in itertools.combinations(root_rows, 2):
        if compatible(a,b):
            base, terms = ordered_query(a, b)
            for query in [base, f"best {base}", f"{base} software"]:
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

def searxng_search(db: Session, query: str, categories="general", limit=10) -> list[dict]:
    base = setting(db, "SEARXNG_URL").rstrip("/")
    if not base:
        return []
    headers = {"Accept": "application/json"}
    token = setting(db, "SEARXNG_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"{base}/search", params={"q": query, "format":"json", "categories":categories, "language":"en"}, headers=headers, timeout=20)
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

def collect_social(db: Session, keyword: models.Keyword) -> list[models.SocialEvidence]:
    db.query(models.SocialEvidence).filter_by(keyword_id=keyword.id).delete()
    rows=[]
    for suffix, platform in [(" site:reddit.com", "reddit"), (" site:news.ycombinator.com", "hn")]:
        for item in searxng_search(db, keyword.query + suffix, limit=3):
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
    verdict = "Action" if total >= 74 and strong_count <= 2 and gap >= .52 and has_social and relevant_count >= 5 else ("Watch" if total >= 55 and relevant_count >= 3 else "Reject")
    evidence = [{"type":"serp","url":s.url,"title":s.title,"tags":json.loads(s.gap_tags or "[]")} for s in serp[:5]] + [{"type":x.platform,"url":x.url,"title":x.title} for x in socials[:4]]
    risks=[]
    if strong_count>3: risks.append("SERP 强品牌过多，切入难度高")
    if len(socials)==0: risks.append("缺少社媒痛点旁证")
    if mismatch_count >= max(2, len(serp)//2): risks.append("SERP 查询意图不匹配，搜索入口不可靠")
    if gap<.5: risks.append("SERP 缺口不明显")
    plan = f"围绕 `{keyword.query}` 做一个单页 MVP：输入关键业务参数，输出可下载结果/模板；首屏解释目标用户、3 个使用场景、FAQ，并用 SearXNG/SERP 证据继续扩展长尾词。"
    card=models.OpportunityCard(keyword_id=keyword.id,title=f"{keyword.query} opportunity", verdict=verdict, score=total, demand_score=round(demand,2), serp_gap_score=round(gap,2), competitor_weakness_score=round(comp,2), mvp_score=mvp, monetization_score=mscore, monetization_type=mtype, mvp_plan=plan, evidence_json=json.dumps(evidence,ensure_ascii=False), risks=json.dumps(risks,ensure_ascii=False))
    db.add(card); keyword.score=total; keyword.status=verdict.lower(); db.commit(); db.refresh(card); return card

def daily_run(db: Session, limit=12, roots=None) -> models.RunHistory:
    run=models.RunHistory(kind="daily", status="running"); db.add(run); db.commit(); db.refresh(run)
    try:
        kws=discover_keywords(db, limit=limit, roots=roots)
        cards=[]
        for kw in kws[:limit]:
            run_serp(db, kw)
            cards.append(make_card(db, kw))
        summary={"keywords":len(kws), "cards":len(cards), "action":sum(1 for c in cards if c.verdict=="Action"), "watch":sum(1 for c in cards if c.verdict=="Watch"), "reject":sum(1 for c in cards if c.verdict=="Reject")}
        run.status="ok"; run.summary=json.dumps(summary, ensure_ascii=False); run.finished_at=datetime.utcnow()
    except Exception as e:
        run.status="failed"; run.summary=str(e); run.finished_at=datetime.utcnow()
    db.commit(); db.refresh(run); return run

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
