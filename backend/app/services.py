from __future__ import annotations
import json, re, itertools, os, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
import requests
from sqlalchemy.orm import Session
from . import models
ROOT = Path(os.environ.get("DEMAND_HUNTER_ROOT", str(Path(__file__).resolve().parents[2])))

DEFAULT_SETTINGS = {
    "SEARXNG_URL": "",
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
    "LLM_CARD_ANALYSIS_ENABLED": "true",
    "LLM_CARD_ANALYSIS_TIMEOUT_SECONDS": "18",
    "LLM_CARD_ANALYSIS_CANDIDATE_LIMIT": "1",
    "AUTO_RUN_ENABLED": "true",
    "AUTO_RUN_INTERVAL_MINUTES": "360",
    "AUTO_RUN_LIMIT": "6",
    "AUTO_RECHECK_ENABLED": "true",
    "AUTO_RECHECK_LIMIT": "4",
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
    "SERP_PROVIDER_ORDER": "searxng,serpapi,zenserp,scaleserp,brave,tavily",
    "SERP_PROVIDER_ATTEMPT_LIMIT": "3",
    "SERP_ROTATION_STRATEGY": "round_robin",
    "COLLECTOR_AUTO_ENABLED": "true",
    "COLLECTOR_AUTO_SEEDS": "invoice calculator,shopify tax app,woocommerce returns,compliance tracker,appointment reminder template",
    "COLLECTOR_AUTO_DOMAINS": "",
    "COLLECTOR_AUTO_LIMIT": "24",
    "COLLECTOR_AUTO_IMPORT_LIMIT": "12",
    "COLLECTOR_AUTO_ADVANCED_ENABLED": "true",
    "COLLECTOR_AUTO_SOURCE_RADAR_ENABLED": "true",
    "COLLECTOR_AUTO_SITEMAP_ENABLED": "true",
    "COLLECTOR_AUTO_SUGGEST_ENABLED": "true",
    "COLLECTOR_ADVANCED_MAX_SECONDS": "90",
    "COLLECTOR_AUTOPILOT_MAX_SECONDS": "120",
    "COLLECTOR_SUGGEST_MAX_SECONDS": "20",
    "COLLECTOR_SOURCE_RADAR_MAX_SECONDS": "45",
    "COLLECTOR_SOURCE_WEIGHTS": "{}",
    "COLLECTOR_AUTO_MIN_WEIGHT": "0.35",
    "REPAIR_EXPERIMENT_COOLDOWN_HOURS": "24",

    # Collector / SEO data provider credentials. Store multiple keys where providers support rotation.
    "BING_WEBMASTER_API_KEYS": "",
    "DATAFORSEO_CREDENTIALS": "",
    "SEMRUSH_API_KEYS": "",
    "AHREFS_API_KEYS": "",
    "SIMILARWEB_API_KEYS": "",
    "SERPAPI_API_KEYS": "",
    "ZENSERP_API_KEYS": "",
    "SCALESERP_API_KEYS": "",
    "YOUTUBE_API_KEYS": "",
    "REDDIT_CREDENTIALS": "",
    "PRODUCTHUNT_TOKENS": "",
    "GITHUB_TOKENS": "",
    "HUGGINGFACE_TOKENS": "",
    "X_BEARER_TOKENS": "",
    "WAPPALYZER_API_KEYS": "",
    "BUILTWITH_API_KEYS": "",
}

API_KEY_TYPES = [
    {"id":"brave", "setting_key":"BRAVE_API_KEYS", "title":"Brave Search API", "category":"SERP", "price":"free_quota", "free_quota":"2,000 queries/month", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":True, "provider":"brave"},
    {"id":"tavily", "setting_key":"TAVILY_API_KEYS", "title":"Tavily Search API", "category":"SERP / Web Research", "price":"free_quota", "free_quota":"1,000 credits/month", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":True, "provider":"tavily"},
    {"id":"serpapi", "setting_key":"SERPAPI_API_KEYS", "title":"SerpApi", "category":"Google SERP", "price":"free_quota", "free_quota":"100 searches/month/account", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":True, "provider":"serpapi"},
    {"id":"zenserp", "setting_key":"ZENSERP_API_KEYS", "title":"Zenserp", "category":"Google SERP", "price":"free_quota", "free_quota":"limited free quota", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":True, "provider":"zenserp"},
    {"id":"scaleserp", "setting_key":"SCALESERP_API_KEYS", "title":"Scale SERP", "category":"Google SERP", "price":"free_quota", "free_quota":"limited free quota", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":True, "provider":"scaleserp"},
    {"id":"dataforseo", "setting_key":"DATAFORSEO_CREDENTIALS", "title":"DataForSEO", "category":"SEO / SERP", "price":"paid_free_trial", "free_quota":"trial/paid credits", "fields":[{"name":"login","label":"Login / Email","secret":False,"kind":"text"},{"name":"password","label":"Password / API Secret","secret":True,"kind":"password"}], "enabled":False, "provider":"dataforseo"},
    {"id":"bing_webmaster", "setting_key":"BING_WEBMASTER_API_KEYS", "title":"Bing Webmaster API", "category":"Webmaster Keyword Data", "price":"free", "free_quota":"free with Bing Webmaster", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"bing_webmaster"},
    {"id":"semrush", "setting_key":"SEMRUSH_API_KEYS", "title":"Semrush API", "category":"SEO", "price":"paid", "free_quota":"paid only / account dependent", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"semrush"},
    {"id":"ahrefs", "setting_key":"AHREFS_API_KEYS", "title":"Ahrefs API", "category":"SEO", "price":"paid", "free_quota":"paid only / account dependent", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"ahrefs"},
    {"id":"similarweb", "setting_key":"SIMILARWEB_API_KEYS", "title":"SimilarWeb API", "category":"Traffic / Competitor", "price":"paid", "free_quota":"paid/trial dependent", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"similarweb"},
    {"id":"youtube", "setting_key":"YOUTUBE_API_KEYS", "title":"YouTube Data API", "category":"Content / Trends", "price":"free_quota", "free_quota":"Google quota based", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"youtube"},
    {"id":"github", "setting_key":"GITHUB_TOKENS", "title":"GitHub Token", "category":"Repo Ecosystem", "price":"free_optional", "free_quota":"higher rate limit with token", "fields":[{"name":"token","label":"Token","secret":True,"kind":"text"}], "enabled":False, "provider":"github"},
    {"id":"huggingface", "setting_key":"HUGGINGFACE_TOKENS", "title":"Hugging Face Token", "category":"AI Model Ecosystem", "price":"free_optional", "free_quota":"higher rate/auth with token", "fields":[{"name":"token","label":"Token","secret":True,"kind":"text"}], "enabled":False, "provider":"huggingface"},
    {"id":"producthunt", "setting_key":"PRODUCTHUNT_TOKENS", "title":"ProductHunt Token", "category":"Launch / Products", "price":"free_limited", "free_quota":"token required", "fields":[{"name":"token","label":"Bearer Token","secret":True,"kind":"text"}], "enabled":False, "provider":"producthunt"},
    {"id":"reddit", "setting_key":"REDDIT_CREDENTIALS", "title":"Reddit API Credentials", "category":"Community", "price":"free_limited", "free_quota":"API policy dependent", "fields":[{"name":"client_id","label":"Client ID","secret":False,"kind":"text"},{"name":"client_secret","label":"Client Secret","secret":True,"kind":"password"},{"name":"user_agent","label":"User Agent","secret":False,"kind":"text"}], "enabled":False, "provider":"reddit"},
    {"id":"x", "setting_key":"X_BEARER_TOKENS", "title":"X / Twitter Bearer Token", "category":"Social", "price":"paid_limited", "free_quota":"limited/paid", "fields":[{"name":"bearer_token","label":"Bearer Token","secret":True,"kind":"text"}], "enabled":False, "provider":"x"},
    {"id":"wappalyzer", "setting_key":"WAPPALYZER_API_KEYS", "title":"Wappalyzer API", "category":"Technology Lookup", "price":"paid_free_trial", "free_quota":"trial dependent", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"wappalyzer"},
    {"id":"builtwith", "setting_key":"BUILTWITH_API_KEYS", "title":"BuiltWith API", "category":"Technology Lookup", "price":"paid", "free_quota":"paid/trial dependent", "fields":[{"name":"api_key","label":"API Key","secret":True,"kind":"text"}], "enabled":False, "provider":"builtwith"},
]

def api_key_type_by_id(type_id: str) -> dict | None:
    return next((x for x in API_KEY_TYPES if x["id"] == type_id), None)

def format_api_key_entry(type_def: dict, payload: dict) -> str:
    fields = type_def.get("fields") or []
    if len(fields) == 1:
        return str(payload.get(fields[0]["name"], "")).strip()
    return json.dumps({f["name"]: str(payload.get(f["name"], "")).strip() for f in fields}, ensure_ascii=False, separators=(",",":"))

DEFAULT_ROOTS = [
    ("invoice", "function"), ("shopify", "vertical"), ("woocommerce", "vertical"), ("quickbooks", "vertical"),
    ("reconciliation", "pain"), ("appointment", "vertical"), ("compliance", "pain"),
    ("contractor", "vertical"), ("clinic", "vertical"), ("rental", "vertical"),
]
DEFAULT_TOOL_ROOT_TERMS = ['action', 'advisor', 'agent', 'ai', 'analyzer', 'anime', 'answer', 'art', 'assistant', 'audio', 'avatar', 'best', 'builder', 'calculator', 'cartoon', 'cataloger', 'character', 'chart', 'chat', 'cheat', 'checker', 'clue', 'code', 'coloring page', 'comparator', 'compiler', 'composer', 'connector', 'constructor', 'convert', 'converter', 'crawler', 'creator', 'dashboard', 'designer', 'detector', 'diagram', 'directory', 'downloader', 'editor', 'emoji', 'enhancer', 'evaluator', 'example', 'explorer', 'extractor', 'face', 'faq', 'figure', 'filter', 'finder', 'font', 'format', 'generator', 'graph', 'guide', 'helper', 'hint', 'how to', 'humanizer', 'icon', 'ideas', 'illustration', 'image', 'interior design', 'interpreter', 'layout', 'list', 'logo', 'maker', 'manager', 'meme', 'model', 'modifier', 'monitor', 'music', 'navigator', 'notifier', 'online', 'optimizer', 'paraphraser', 'pattern', 'photo', 'picture', 'planner', 'portal', 'portrait', 'processor', 'product photo', 'receiver', 'recommend', 'recorder', 'resources', 'responder', 'restorer', 'review', 'sample', 'scheduler', 'scraper', 'sender', 'simulator', 'solver', 'song', 'sound', 'speech', 'starter', 'studio', 'style', 'summarizer', 'summary', 'syncer', 'tattoo', 'template', 'tester', 'text']
DEFAULT_ROOTS += [(term, "tool") for term in DEFAULT_TOOL_ROOT_TERMS if term not in {t for t, _ in DEFAULT_ROOTS}]
INTENT_WORDS = {"template":"seo_tool", "calculator":"seo_tool", "generator":"seo_tool", "tracker":"workflow_tool", "dashboard":"workflow_saas", "integration":"workflow_saas", "automation":"workflow_saas", "reconciliation":"workflow_saas"}
STRONG_DOMAINS = ("google.com","microsoft.com","adobe.com","shopify.com","intuit.com","hubspot.com","salesforce.com","wikipedia.org","amazon.com","booking.com","expedia.com","kayak.com")
FORUM_DOMAINS = ("reddit.com","news.ycombinator.com","stackoverflow.com","quora.com","community.","forum.")
WEAK_HINTS = ("free", "blog", "post", "forum", "reddit", "template", "spreadsheet", "pdf", "docs", "github")
BLOCKED_AMBIGUOUS_ROOTS = {"booking"}

_KEY_POOL_STATE: dict[str, dict] = {}


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

def normalized_opportunity_key(text: str) -> str:
    s=re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", (text or "").lower())
    drop={"best","top","free","online","software","tool","tools","app","apps","website","web","service","services","机会","任务","围绕","针对","面向","的","和","与","做"}
    out=[]
    for t in s.split():
        if t in drop:
            continue
        if t not in out:
            out.append(t)
    return " ".join(out[:10])

def opportunity_similarity(a: str, b: str) -> float:
    ta=set(normalized_opportunity_key(a).split())
    tb=set(normalized_opportunity_key(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))

def keyword_noise_reason(query: str, source: str = "") -> str:
    q=(query or "").lower()
    if any(x in q for x in ("pull request", "fix activejob", "attempt to", " labels ", "github", "documentation", "readme", "release notes", "changelog")):
        return "developer_or_documentation_noise"
    if re.search(r"\b(after|before)\b", q):
        return "search_operator_noise"
    if re.search(r"^[a-z0-9][a-z0-9 ._-]{1,24}:\s+", q) or re.search(r"\bwhich\s+.+\bbest\b", q) or re.search(r"\bfor\s+your\s+(small\s+)?business\b", q) or q.rstrip().endswith("?"):
        return "title_or_brand_residue"
    if re.search(r"\b(best|top)\b.+\b(plugin|plugins|extension|extensions|software|apps?)\b", q) or re.search(r"\b(plugin|plugins|extension|extensions)\b.+\b(compared|comparison|review|reviews)\b", q) or re.search(r"\b(compared|comparison|review|reviews)\b", q):
        return "comparison_or_listicle_intent"
    if re.search(r"\b(woocommerce|shopify|wordpress)\b", q) and re.search(r"\b(extension|plugin|plugins|marketplace)\b", q) and not re.search(r"\b(template|calculator|checklist|tracker|generator|automation|dashboard|workflow)\b", q):
        return "plugin_product_title_residue"
    if re.search(r"\b\d{8,}\b", q) or re.search(r"\b(activity|post|tweet|status|story)\s+\d{5,}\b", q):
        return "social_activity_id_noise"
    if len(q.split()) <= 2 and not re.search(r"\b(calculator|template|generator|tracker|checklist|converter|analyzer|detector|builder|planner|scheduler)\b", q):
        return "generic_short_tail"
    if re.search(r"\bhow to\b", q) and not re.search(r"\b(template|calculator|generator|tracker|checklist|dashboard|workflow|automation|software)\b", q):
        return "tutorial_intent_not_tool"
    plural_map={"calculators":"calculator","generators":"generator","templates":"template","checkers":"checker","converters":"converter","trackers":"tracker","dashboards":"dashboard","analyzers":"analyzer","builders":"builder","planners":"planner","estimators":"estimator","forms":"form","spreadsheets":"spreadsheet","reports":"report","monitors":"monitor","automations":"automation","integrations":"integration","apis":"api"}
    terms=[plural_map.get(t,t) for t in normalized_opportunity_key(query).split()]
    if len(terms) < 2:
        return "too_short"
    if len(terms) > 9:
        return "too_long"
    # Generic calculator/template variants without a vertical or concrete job tend
    # to create duplicate pseudo-opportunities.
    if any(t in terms for t in {"calculator","template","generator"}) and not any(t in terms for t in {"invoice","tax","compliance","appointment","rental","clinic","shopify","woocommerce","hubspot","quickbooks","stripe","permit","contractor","patient","payment","fee","late","reminder","estimate"}):
        return "generic_tool_modifier"
    tool_count=len(set(terms) & {"calculator","template","generator","checker","converter","tracker","dashboard","analyzer","builder","planner","estimator","form","spreadsheet"})
    commercial_count=len(set(terms) & {"invoice","tax","compliance","shopify","woocommerce","quickbooks","hubspot","salesforce","stripe","paypal","business","agency","client","contractor","clinic","rental","payment","fee","late","reminder","estimate"})
    if len(terms) >= 3 and terms[0] in {"calculator","template","generator","tool","software","app"} and tool_count >= 2:
        return "tool_category_slug"
    if tool_count >= 2 and commercial_count <= 1:
        return "tool_word_stack"
    return ""

def find_duplicate_card(db: Session, keyword: models.Keyword, threshold: float = 0.42) -> models.OpportunityCard | None:
    target=keyword.query
    target_terms=set(normalized_opportunity_key(target).split())
    rows=(db.query(models.OpportunityCard)
        .join(models.Keyword, models.Keyword.id == models.OpportunityCard.keyword_id)
        .order_by(models.OpportunityCard.created_at.desc())
        .limit(80).all())
    for card in rows:
        existing_kw=db.get(models.Keyword, card.keyword_id)
        if not existing_kw or existing_kw.id == keyword.id:
            continue
        existing_terms=set(normalized_opportunity_key(existing_kw.query).split())
        # A reviewed Reject/Block must not suppress a more specific later
        # opportunity. Example: old generic "compliance calculator" Reject should
        # not swallow "compliance cost calculator" when the user may adopt it.
        if card.feedback_label in {"Reject","Block"} or card.verdict in {"Reject","Block"}:
            if len(target_terms - existing_terms) >= 1 or len(target_terms) > len(existing_terms):
                continue
        sim=max(opportunity_similarity(target, existing_kw.query), opportunity_similarity(target, card.title))
        if sim >= threshold:
            return card
    return None

def append_duplicate_evidence(db: Session, card: models.OpportunityCard, keyword: models.Keyword, similarity_note: str = "") -> models.OpportunityCard:
    """Attach a duplicate/variant keyword to the main opportunity evidence chain.

    Duplicate does not mean delete. It means this keyword becomes supporting
    evidence for the canonical opportunity card so the signal is preserved and
    traceable.
    """
    try:
        evidence=json.loads(card.evidence_json or "[]")
        if not isinstance(evidence, list): evidence=[evidence]
    except Exception:
        evidence=[]
    marker={
        "type":"duplicate_keyword_evidence",
        "keyword_id":keyword.id,
        "keyword":keyword.query,
        "source":keyword.source,
        "score":keyword.score,
        "intent":keyword.intent,
        "note":similarity_note or "Merged as evidence chain; not deleted.",
    }
    exists=any(isinstance(x,dict) and x.get("type")=="duplicate_keyword_evidence" and x.get("keyword_id")==keyword.id for x in evidence)
    if not exists:
        evidence.append(marker)
        card.evidence_json=json.dumps(evidence, ensure_ascii=False)
    keyword.status="duplicate_evidence"
    keyword.intent=f"evidence_for_card:{card.id}"[:80]
    db.merge(keyword); db.merge(card); db.commit(); db.refresh(card)
    return card

def opportunity_group_for_card(db: Session, card: models.OpportunityCard) -> dict:
    """Build a user-facing opportunity group around a representative card.

    A card is only the current representative. Similar keywords, duplicate
    variants, archived/rejected candidates, and older cards should remain as a
    supporting evidence chain. The group probability estimates how likely the
    cluster is a real opportunity, not whether one keyword string is perfect.
    """
    kw=db.get(models.Keyword, card.keyword_id)
    canonical=normalized_opportunity_key(kw.query if kw else card.title)
    group_terms=[t for t in canonical.split() if t not in {"ai","best","top","software","app","tool","online","free"}]
    group_key=" ".join(group_terms) or canonical
    terms=set(group_key.split())
    evidence=[]
    try:
        raw=json.loads(card.evidence_json or "[]")
        if isinstance(raw, list): evidence.extend([x for x in raw if isinstance(x,dict)])
    except Exception:
        pass
    variant_keyword_ids={int(x.get("keyword_id")) for x in evidence if x.get("type")=="duplicate_keyword_evidence" and x.get("keyword_id")}
    keyword_rows=[]
    if kw: keyword_rows.append(kw)
    for kid in variant_keyword_ids:
        row=db.get(models.Keyword, kid)
        if row and row.id not in {x.id for x in keyword_rows}: keyword_rows.append(row)
    # Also find close variants not yet explicitly merged. Keep this bounded.
    for row in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(300).all():
        if row.id in {x.id for x in keyword_rows}: continue
        rterms=set(normalized_opportunity_key(row.query).split())
        if not rterms or not terms: continue
        overlap=len(terms & rterms)/max(1, min(len(terms), len(rterms)))
        if overlap >= 0.66 and ("calculator" in terms or "template" in terms or "tracker" in terms or "automation" in terms):
            keyword_rows.append(row)
        if len(keyword_rows)>=18: break
    card_rows=[]
    for row in keyword_rows:
        card_rows.extend(db.query(models.OpportunityCard).filter_by(keyword_id=row.id).all())
    candidate_rows=[]
    for cand in db.query(models.CandidateKeyword).order_by(models.CandidateKeyword.created_at.desc()).limit(600).all():
        cterms=set(normalized_opportunity_key(cand.keyword).split())
        if not cterms or not terms: continue
        overlap=len(terms & cterms)/max(1, min(len(terms), len(cterms)))
        if overlap>=0.66:
            candidate_rows.append(cand)
        if len(candidate_rows)>=30: break
    sources=sorted({x.source for x in keyword_rows if x.source} | {x.source for x in candidate_rows if x.source})
    variants=[]; seen=set()
    for row in keyword_rows:
        if row.query in seen: continue
        seen.add(row.query)
        variants.append({"type":"keyword","id":row.id,"keyword":row.query,"source":row.source,"status":row.status,"score":row.score,"intent":row.intent})
    for cand in candidate_rows[:20]:
        if cand.keyword in seen: continue
        seen.add(cand.keyword)
        variants.append({"type":"candidate","id":cand.id,"keyword":cand.keyword,"source":cand.source,"status":cand.status,"score":cand.score,"method":cand.method,"source_url":cand.source_url})
    positive=sum(1 for c in card_rows if c.verdict in {"Adopted","Action","Watch"} or c.feedback_label in {"Adopted","Action","Watch"})
    negative=sum(1 for c in card_rows if c.verdict in {"Reject","Block"} or c.feedback_label in {"Reject","Block"})
    archived=sum(1 for v in variants if str(v.get("status") or "").startswith("archived"))
    explicit_action=any(c.feedback_label in {"Adopted","Action"} or c.verdict in {"Adopted","Action"} for c in card_rows)
    base=0.25
    base += min(0.24, 0.04*len(variants))
    base += min(0.18, 0.04*len(sources))
    base += min(0.22, 0.08*positive)
    base -= min(0.18, 0.05*negative)
    if explicit_action: base += 0.18
    probability=round(max(0.05, min(0.98, base)), 2)
    if probability>=0.78: label="高置信机会组"
    elif probability>=0.58: label="可继续验证机会组"
    else: label="弱信号机会组"
    return {
        "group_id": f"og-{hashlib.sha1(group_key.encode('utf-8')).hexdigest()[:10]}",
        "group_key": group_key,
        "canonical_keyword": group_key or canonical or (kw.query if kw else card.title),
        "representative_card_id": card.id,
        "probability": probability,
        "label": label,
        "evidence_count": len(variants)+len(card_rows),
        "variant_count": len(variants),
        "source_count": len(sources),
        "positive_cards": positive,
        "negative_cards": negative,
        "archived_items": archived,
        "sources": sources,
        "variants": variants[:24],
    }

def grouped_opportunity_cards(db: Session, verdict: str = "All", limit: int = 300) -> list[models.OpportunityCard]:
    """Return representative cards by opportunity group with one canonical ranking.

    This is the single source of truth for overview counts and opportunity list.
    """
    try: min_action=float(setting(db,"MIN_ACTION_SCORE") or "74")
    except Exception: min_action=74.0
    rows=db.query(models.OpportunityCard).order_by(models.OpportunityCard.created_at.desc()).limit(limit).all()
    def final(c): return c.feedback_label or c.verdict
    by={}
    def rank(c):
        fv=final(c)
        group=opportunity_group_for_card(db,c)
        return ({"Adopted":5,"Action":4,"Watch":3,"Reject":1,"Block":0}.get(fv,1))*1000 + float(c.score or 0) + float(group.get("probability") or 0)*100
    # First pick one representative/final state per group across ALL cards.
    # Filtering before grouping is wrong: if a group has one Adopted card and
    # one older Action variant, it must live under Adopted only, not both.
    for c in rows:
        gid=opportunity_group_for_card(db,c).get("group_id") or f"card-{c.id}"
        if gid not in by or rank(c)>rank(by[gid]): by[gid]=c
    reps=list(by.values())
    filtered=[]
    for c in reps:
        fv=final(c)
        ok = verdict=="All" or fv==verdict
        if ok and verdict=="Action" and not c.feedback_label: ok=float(c.score or 0)>=min_action
        if ok: filtered.append(c)
    return sorted(filtered, key=lambda c: (rank(c), c.created_at), reverse=True)

def opportunity_group_counts(db: Session) -> dict:
    adopted=len(grouped_opportunity_cards(db,"Adopted"))
    action=len(grouped_opportunity_cards(db,"Action"))
    watch=len(grouped_opportunity_cards(db,"Watch"))
    reject=len(grouped_opportunity_cards(db,"Reject"))
    block=len(grouped_opportunity_cards(db,"Block"))
    # Overview total must equal the visible status buckets exactly.
    return {"cards": adopted+action+watch+reject+block, "adopted": adopted, "action": action, "watch": watch, "reject": reject, "block": block, "unit":"opportunity_group"}

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
    for query, terms in candidates:
        row = db.query(models.Keyword).filter_by(query=query).first()
        if row and row.status in {"reject", "rejected", "block", "duplicate", "serp_reject", "rewrite_exhausted"}:
            continue
        if keyword_noise_reason(query, "root_combo"):
            continue
        if not row:
            row = models.Keyword(query=query, source="root_combo", root_terms=json.dumps(terms), intent=classify_intent(query))
            db.add(row); db.flush()
        out.append(row)
        if len(out) >= limit:
            break
    db.commit()
    return out

def discover_keywords_four_find(db: Session, limit=24, seeds: list[str] | None = None) -> list[models.Keyword]:
    """Discover/import keywords through the Four-Find service path.

    This keeps discovery as a backend/API capability rather than a shell script.
    """
    import time as _time
    _ff_start = _time.monotonic()
    _ff_max = 35  # total budget in seconds for Four-Find discovery
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
        if _time.monotonic() - _ff_start > _ff_max:
            break
        four_find.find_keywords_from_site(db, domain, searxng_search, limit=8)
        similar = four_find.find_similar_sites(db, domain, searxng_search, limit=4)
        for site in similar[:2]:
            if _time.monotonic() - _ff_start > _ff_max:
                break
            four_find.find_keywords_from_site(db, site.similar_domain, searxng_search, limit=4)
        for kw in four_find.import_discovered_keywords(db, limit=max(1, min(import_limit, limit))):
            if kw.query not in seen:
                seen.add(kw.query); out.append(kw)
            if len(out) >= limit:
                return out
    per_seed = max(1, min(import_limit, limit) // max(1, len(seeds)))
    for seed in seeds:
        if _time.monotonic() - _ff_start > _ff_max:
            print(f"[four_find] budget exceeded, stopping at seed={seed}", flush=True)
            break
        _seed_start = _time.monotonic()
        _seed_timeout = 15  # per-seed budget
        # run_four_find_and_import doesn't accept a timeout; wrap in a simple elapsed check
        # by calling with depth=1 when budget is tight
        remaining_budget = _ff_max - (_time.monotonic() - _ff_start)
        use_depth = 2 if remaining_budget > 25 else 1
        four_find.run_four_find_and_import(db, seed, searxng_search, depth=use_depth, import_limit=per_seed)
        print(f"[four_find] seed={seed} depth={use_depth} done, elapsed={_time.monotonic()-_ff_start:.1f}s", flush=True)
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
    return [entry["key"] for entry in provider_key_pool(db, multi_key, single_key)]

def _fingerprint_secret(value: str) -> str:
    value = value or ""
    if len(value) <= 8:
        return "***"
    return f"***{value[-4:]}"

def provider_key_pool(db: Session, multi_key: str, single_key: str = "") -> list[dict]:
    """Return ordered key entries and advance cursor when strategy is round_robin.

    This is the real key-pool layer used by paid/free-quota APIs. It tracks
    success/failure counters in memory and exposes stable key indexes so callers
    can record results. Persistence is intentionally avoided for secrets/status;
    settings remain the source of keys.
    """
    keys = _split_multi_value(setting(db, multi_key))
    if not keys and single_key:
        single = (setting(db, single_key) or "").strip()
        if single:
            keys = [single]
    if not keys:
        return []
    state = _KEY_POOL_STATE.setdefault(multi_key, {"cursor": 0, "stats": {}})
    indexed = [{"index": i, "key": k, "masked": _fingerprint_secret(k), "stats": state["stats"].get(str(i), {})} for i, k in enumerate(keys)]
    if serp_rotation_strategy(db) == "round_robin":
        idx = int(state.get("cursor", 0)) % len(indexed)
        state["cursor"] = idx + 1
        indexed = indexed[idx:] + indexed[:idx]
    return indexed

def record_provider_key_result(pool_key: str, index: int | None, ok: bool, error: str = ""):
    if index is None:
        return
    state = _KEY_POOL_STATE.setdefault(pool_key, {"cursor": 0, "stats": {}})
    stats = state.setdefault("stats", {}).setdefault(str(index), {"ok": 0, "fail": 0, "last_error": ""})
    if ok:
        stats["ok"] = int(stats.get("ok", 0)) + 1
        stats["last_error"] = ""
    else:
        stats["fail"] = int(stats.get("fail", 0)) + 1
        stats["last_error"] = str(error)[-240:]

def provider_key_pool_status(db: Session, multi_key: str, single_key: str = "") -> dict:
    entries = provider_key_pool(db, multi_key, single_key)
    return {"key": multi_key, "count": len(entries), "strategy": serp_rotation_strategy(db), "items": [{"index": e["index"], "masked": e["masked"], "stats": e.get("stats", {})} for e in entries]}

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
    keys = provider_key_pool(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")
    if not keys:
        return []
    last_error = ""
    for entry in keys:
      try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": min(max(limit, 1), 20), "search_lang": "en"},
            headers={"Accept": "application/json", "X-Subscription-Token": entry["key"]},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        out=[]
        for item in (data.get("web", {}) or {}).get("results", [])[:limit]:
            out.append({"title": item.get("title") or "", "url": item.get("url") or "", "content": item.get("description") or "", "engine": "brave", "provider_key": entry["masked"]})
        record_provider_key_result("BRAVE_API_KEYS", entry["index"], True)
        return out
      except Exception as e:
        last_error = str(e)
        record_provider_key_result("BRAVE_API_KEYS", entry.get("index"), False, last_error)
        continue
    return [{"title":"Brave error", "url":"", "content":last_error, "engine":"error"}]

def tavily_search(db: Session, query: str, limit=10) -> list[dict]:
    keys = provider_key_pool(db, "TAVILY_API_KEYS", "TAVILY_API_KEY")
    if not keys:
        return []
    last_error = ""
    for entry in keys:
      try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": entry["key"], "query": query, "max_results": min(max(limit, 1), 10), "search_depth": "basic", "include_answer": False},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        out=[]
        for item in data.get("results", [])[:limit]:
            out.append({"title": item.get("title") or "", "url": item.get("url") or "", "content": item.get("content") or "", "engine": "tavily", "provider_key": entry["masked"]})
        record_provider_key_result("TAVILY_API_KEYS", entry["index"], True)
        return out
      except Exception as e:
        last_error = str(e)
        record_provider_key_result("TAVILY_API_KEYS", entry.get("index"), False, last_error)
        continue
    return [{"title":"Tavily error", "url":"", "content":last_error, "engine":"error"}]

def serpapi_search(db: Session, query: str, limit=10) -> list[dict]:
    keys = provider_key_pool(db, "SERPAPI_API_KEYS")
    if not keys:
        return []
    last_error = ""
    for entry in keys:
        try:
            r = requests.get(
                "https://serpapi.com/search.json",
                params={"engine": "google", "q": query, "api_key": entry["key"], "num": min(max(limit, 1), 10), "hl": "en"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                raise RuntimeError(data.get("error"))
            out=[]
            for item in (data.get("organic_results") or [])[:limit]:
                out.append({"title": item.get("title") or "", "url": item.get("link") or "", "content": item.get("snippet") or "", "engine": "serpapi", "provider_key": entry["masked"]})
            # Include related searches as low-rank discovery hints when present.
            for item in (data.get("related_searches") or [])[:max(0, limit-len(out))]:
                q = item.get("query") or item.get("title") or ""
                if q:
                    out.append({"title": q, "url": item.get("link") or "", "content": "related_search", "engine": "serpapi_related", "provider_key": entry["masked"]})
            record_provider_key_result("SERPAPI_API_KEYS", entry["index"], True)
            return out
        except Exception as e:
            last_error = str(e)
            record_provider_key_result("SERPAPI_API_KEYS", entry.get("index"), False, last_error)
            continue
    return [{"title":"SerpApi error", "url":"", "content":last_error, "engine":"error"}]

def zenserp_search(db: Session, query: str, limit=10) -> list[dict]:
    keys = provider_key_pool(db, "ZENSERP_API_KEYS")
    if not keys:
        return []
    last_error = ""
    for entry in keys:
        try:
            r = requests.get(
                "https://app.zenserp.com/api/v2/search",
                params={"q": query, "apikey": entry["key"], "num": min(max(limit, 1), 10), "hl": "en", "gl": "us"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                raise RuntimeError(data.get("error"))
            out=[]
            for item in (data.get("organic") or [])[:limit]:
                out.append({"title": item.get("title") or "", "url": item.get("url") or "", "content": item.get("desc") or item.get("snippet") or "", "engine": "zenserp", "provider_key": entry["masked"]})
            record_provider_key_result("ZENSERP_API_KEYS", entry["index"], True)
            return out
        except Exception as e:
            last_error = str(e)
            record_provider_key_result("ZENSERP_API_KEYS", entry.get("index"), False, last_error)
            continue
    return [{"title":"Zenserp error", "url":"", "content":last_error, "engine":"error"}]

def scaleserp_search(db: Session, query: str, limit=10) -> list[dict]:
    keys = provider_key_pool(db, "SCALESERP_API_KEYS")
    if not keys:
        return []
    last_error = ""
    for entry in keys:
        try:
            r = requests.get(
                "https://api.scaleserp.com/search",
                params={"q": query, "api_key": entry["key"], "num": min(max(limit, 1), 10), "hl": "en", "gl": "us", "output": "json"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                raise RuntimeError(data.get("error"))
            out=[]
            for item in (data.get("organic_results") or [])[:limit]:
                out.append({"title": item.get("title") or "", "url": item.get("link") or item.get("url") or "", "content": item.get("snippet") or item.get("description") or "", "engine": "scaleserp", "provider_key": entry["masked"]})
            record_provider_key_result("SCALESERP_API_KEYS", entry["index"], True)
            return out
        except Exception as e:
            last_error = str(e)
            record_provider_key_result("SCALESERP_API_KEYS", entry.get("index"), False, last_error)
            continue
    return [{"title":"Scale SERP error", "url":"", "content":last_error, "engine":"error"}]

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
        elif p == "serpapi" and rotating_api_keys(db, "SERPAPI_API_KEYS", ""):
            out.append(p)
        elif p == "zenserp" and rotating_api_keys(db, "ZENSERP_API_KEYS", ""):
            out.append(p)
        elif p == "scaleserp" and rotating_api_keys(db, "SCALESERP_API_KEYS", ""):
            out.append(p)
    return out or ["searxng"]

def provider_search(db: Session, provider: str, query: str, limit=10) -> list[dict]:
    if provider == "brave": return brave_search(db, query, limit)
    if provider == "tavily": return tavily_search(db, query, limit)
    if provider == "serpapi": return serpapi_search(db, query, limit)
    if provider == "zenserp": return zenserp_search(db, query, limit)
    if provider == "scaleserp": return scaleserp_search(db, query, limit)
    return searxng_search(db, query, limit=limit)

def domain(url: str) -> str:
    try: return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception: return ""

def _llm_candidates(db: Session) -> list[dict]:
    rows=[]
    primary_base=(setting(db,"LLM_PRIMARY_BASE_URL") or "").strip().rstrip("/")
    primary_model=(setting(db,"LLM_PRIMARY_MODEL") or "").strip()
    primary_key=(setting(db,"LLM_PRIMARY_API_KEY") or "").strip()
    if primary_base and primary_model:
        rows.append({"base_url": primary_base, "model": primary_model, "api_key": primary_key, "name": "primary"})
    try:
        fallbacks=json.loads(setting(db,"LLM_FALLBACKS") or "[]")
        if isinstance(fallbacks,list):
            for i,row in enumerate(fallbacks):
                if not isinstance(row,dict): continue
                base=(row.get("base_url") or row.get("provider") or "").strip().rstrip("/")
                model=(row.get("model") or "").strip()
                if base and model:
                    rows.append({"base_url": base, "model": model, "api_key": (row.get("api_key") or "").strip(), "name": f"fallback_{i+1}"})
    except Exception:
        pass
    return rows

def _extract_json_object(text: str) -> dict | None:
    text=(text or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text=re.sub(r"^```(?:json)?\s*", "", text)
        text=re.sub(r"\s*```$", "", text)
    try:
        data=json.loads(text)
        return data if isinstance(data,dict) else None
    except Exception:
        pass
    m=re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data=json.loads(m.group(0))
        return data if isinstance(data,dict) else None
    except Exception:
        return None

def _llm_json(db: Session, system: str, user: str, temperature: float = 0.2) -> dict | None:
    try:
        candidate_limit=int(setting(db,"LLM_CARD_ANALYSIS_CANDIDATE_LIMIT") or "1")
    except Exception:
        candidate_limit=1
    try:
        timeout_seconds=float(setting(db,"LLM_CARD_ANALYSIS_TIMEOUT_SECONDS") or "18")
    except Exception:
        timeout_seconds=18.0
    for cfg in _llm_candidates(db)[:max(1,candidate_limit)]:
        url = cfg["base_url"] if cfg["base_url"].endswith("/chat/completions") else f"{cfg['base_url']}/chat/completions"
        headers={"Content-Type":"application/json"}
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        payload={
            "model": cfg["model"],
            "messages":[{"role":"system","content":system},{"role":"user","content":user}],
            "temperature": temperature,
            "response_format": {"type":"json_object"},
        }
        try:
            r=requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
            r.raise_for_status()
            data=r.json()
            content=((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            obj=_extract_json_object(content)
            if obj:
                obj["_llm_provider"] = cfg.get("name")
                return obj
        except Exception:
            continue
    return None

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
    if any(w in q for w in ["shopify", "woocommerce"]) and any(w in q for w in ["tax", "api", "sales tax"]): return "垂直 SaaS / API 集成订阅", 0.78
    if any(w in q for w in ["calculator","template","generator"]): return "SEO 工具 + 广告/联盟/线索捕获", 0.75
    if any(w in q for w in ["integration","sync","automation","dashboard","reconciliation"]): return "垂直微型 SaaS 订阅", 0.8
    if "compliance" in q: return "线索捕获 + 付费报告", 0.65
    return "内容/工具站 + 联盟变现", 0.5

def business_profile(query: str, intent: str, monetization_type: str) -> dict:
    """Business-layer interpretation for opportunity cards.

    This turns SERP/search evidence into a decision-oriented business brief:
    who cares, what triggers payment, the wedge, and the first validation step.
    """
    q = query.lower()
    icp = "SEO 流量运营者 / 垂直工具站建设者"
    pain = "用户想要比通用搜索结果更快、更可操作的自助答案。"
    pay_trigger = "当输出能节省时间、避免错误，或可复用于工作流时，用户才有付费动机。"
    wedge = "做一个单一用途工具，用更清晰的体验和更好的长尾覆盖，避开泛内容页。"
    revenue_path = "SEO 入口 → 免费工具 → 邮箱捕获 → 付费模板/工具包。"
    pricing = "一次性 $9-$29 模板/工具包；如果购买意图弱，则走联盟或线索变现。"
    commercial_mvp = "先做聚焦落地页和一个可付费/可导出的结果，在深入开发前验证购买意图。"
    first_sale_test = [
        "在落地页上直接放明确的付费 offer。",
        "在继续做深产品前，先放 checkout / waitlist 按钮。",
        "衡量购买意图：结账点击、邮箱留资、回复率或付费预订。",
    ]
    gtm = "长尾 SEO + 对比页 + 模板/工具目录分发。"
    commercial_score = 0.55
    business_type = "内容/工具站 + 联盟变现"
    if any(w in q for w in ["shopify", "woocommerce"]) and any(w in q for w in ["tax", "sales tax", "api"]):
        icp = "跨州销售的 Shopify / WooCommerce 店主，以及为他们做结账、税务和合规集成的开发者/代理商"
        pain = "销售税规则、州 nexus、税率 API、Checkout/订单税行和申报工具之间容易错配；商家需要确认现有平台税务能力是否够用，开发者需要更快接入税务计算/校验。"
        pay_trigger = "当店铺开始跨州销售、遇到税务设置不确定、或需要把外部税务 API 接入 Shopify/WooCommerce 订单流程时，才有明确付费动机。"
        wedge = "不是泛泛写 Shopify tax 教程，而是做一个 sales-tax API readiness checker：输入平台、销售州、nexus 状态和现有插件，输出是否需要 Avalara/TaxCloud/Zamp 等 API、缺口清单和接入步骤。"
        business_type = "垂直 SaaS / API 集成线索捕获"
        commercial_mvp = "做一个 Shopify/WooCommerce sales-tax API readiness checker，输出税务 API 需求判断、集成清单和供应商对比 CTA。"
        revenue_path = "SEO/API 搜索入口 → 免费 readiness check → 邮箱/店铺信息捕获 → 税务 API 联盟/实施服务/轻量监控订阅。"
        pricing = "$49-$199 一次性设置审计；或 $29-$99/月销售税配置监控/提醒；也可走税务 API/插件联盟佣金。"
        first_sale_test = ["上线 readiness checker 并追踪提交率", "提供 $99 Shopify sales-tax setup audit CTA", "测试税务 API 供应商推荐/联盟点击"]
        gtm = "Shopify/WooCommerce 税务长尾 SEO + 开发者文档对比页 + agency/税务顾问渠道。"
        commercial_score = 0.66
    elif any(w in q for w in ["appointment", "patient", "clinic", "dental", "salon"]):
        icp = "小诊所 / 预约密集型本地服务商"
        pain = "他们需要可复用的预约模板、提醒、取消/改期流程或 intake 表单。"
        pay_trigger = "当爽约、行政时间和沟通不一致造成可见成本时，才会付费。"
        wedge = "针对窄垂直行业做模板 + 工作流包，而不是泛预约博客文章。"
        business_type = "模板包 → 线索捕获 → 轻量 SaaS"
        commercial_mvp = "做垂直模板/工作流包，用下载门槛和付费定制 CTA 验证需求。"
        revenue_path = "免费模板 → 邮箱捕获 → 付费工作流包 → 设置/服务加售。"
        pricing = "$19-$79 模板/工作流包；如果垂直痛点强，可卖 $199-$499 设置服务。"
        first_sale_test = ["销售一个 3 件套垂直模板包", "增加设置咨询 CTA", "在做 SaaS 前，先让下载用户为定制付费"]
        gtm = "垂直 SEO 页面 + 本地服务社区 + 对小诊所/服务商冷启动触达。"
        commercial_score = 0.68
    elif any(w in q for w in ["invoice", "late fee", "payment", "estimate", "tax", "calculator"]):
        icp = "自由职业者 / 承包商 / 小企业财务负责人"
        pain = "他们需要快速、可解释的发票、费用、报价或付款提醒计算。"
        pay_trigger = "当计算准确性或专业输出直接影响收款时，才会付费。"
        wedge = "不是普通计算器，而是带可打印/可导出的发票或付款结果。"
        business_type = "SEO 计算器 → 联盟/线索磁铁 → 付费模板"
        commercial_mvp = "做一个带导出/打印结果的计算器，并在结果页测试付费包或联盟 CTA。"
        revenue_path = "计算器流量 → 导出/付费墙 CTA → 付费包或会计工具联盟。"
        pricing = "$9-$29 一次性工具包；如果出现会计/支付意图，可测试 CPA 联盟。"
        first_sale_test = ["增加付费导出/模板 CTA", "跟踪“计算 → 导出 → 结账”点击", "测试联盟 CTA 和付费包 CTA 哪个更强"]
        gtm = "SEO 计算器页 + 长尾费用/税务/付款查询 + 财务模板目录。"
        commercial_score = 0.62
    elif any(w in q for w in ["compliance", "audit", "vendor", "training", "permit", "renewal"]):
        icp = "小型监管行业的运营/合规负责人"
        pain = "他们需要避免错过截止日期、审计、续期或供应商合规缺口。"
        pay_trigger = "当合规遗漏带来财务、法律或运营风险时，才会付费。"
        wedge = "针对一个窄法规/流程做截止日期和清单追踪，而不是泛合规平台。"
        business_type = "线索捕获 + 付费报告/模板 → 垂直微型 SaaS"
        commercial_mvp = "做一个能导出合规材料的清单/追踪器，用来测试付费报告或订阅意图。"
        revenue_path = "免费清单/追踪器 → 付费合规包/报告 → 线索或订阅工作流。"
        pricing = "$49-$199 付费合规包/报告；如果验证出重复截止日期痛点，再做 $29-$99/月追踪器。"
        first_sale_test = ["卖出一份合规清单/报告", "导出前要求工作邮箱", "在做订阅软件前先访谈用户"]
        gtm = "窄合规 SEO + 专业社区 + 与顾问合作。"
        commercial_score = 0.72
    go_no_go = "Go" if commercial_score >= 0.68 else ("Watch" if commercial_score >= 0.58 else "No-Go")
    key_assumption = "用户会为更具体、可直接用于工作流的输出付费，而不只是消费免费泛内容。"
    return {"type":"business", "business_type": business_type, "icp": icp, "pain": pain, "pay_trigger": pay_trigger, "wedge": wedge, "commercial_mvp": commercial_mvp, "revenue_path": revenue_path, "pricing": pricing, "gtm": gtm, "first_sale_test": first_sale_test, "commercial_score": commercial_score, "go_no_go": go_no_go, "key_assumption": key_assumption, "monetization": monetization_type}


def _zh_verdict_reason(verdict: str, total: float, gap: float, strong_count: int, relevant_count: int, has_social: bool, require_social: bool, mismatch_count: int) -> str:
    parts = [f"总分 {total}", f"搜索缺口 {round(gap,2)}", f"相关结果 {relevant_count}", f"强品牌 {strong_count}", f"意图不匹配 {mismatch_count}"]
    if require_social:
        parts.append("有社媒旁证" if has_social else "缺少社媒旁证")
    if verdict == "Action":
        return "行动理由：" + "；".join(parts) + "。证据达到当前 Action 门槛，可以进入小规模验证。"
    if verdict == "Watch":
        return "观察理由：" + "；".join(parts) + "。方向可能成立，但证据还不足以直接执行，需要补强需求/社媒/搜索缺口证据。"
    return "拒绝理由：" + "；".join(parts) + "。当前搜索入口或证据质量不足，不建议包装成机会。"

def _keyword_task_detail(keyword_query: str) -> dict:
    ql = keyword_query.lower()
    if any(w in ql for w in ["shopify", "woocommerce"]) and any(w in ql for w in ["tax", "sales tax", "api"]):
        return {"task":"判断 Shopify/WooCommerce 店铺是否需要外部 sales-tax API，并列出接入/配置缺口", "artifact":"销售税 API readiness report + 平台配置清单 + 供应商对比/实施 CTA", "test":"让店主或 agency 输入店铺平台、销售州和 nexus 状态，测试是否愿意预约 $99 设置审计或点击税务 API 推荐"}
    if "late fee" in ql or "rental" in ql:
        return {"task":"生成一份可发送给租客的 late fee notice，并自动计算滞纳金、宽限期和付款截止日", "artifact":"滞纳金通知模板 + 金额计算 + 可复制邮件/短信文本", "test":"让房东/物业用户填写租金、到期日、州/合同规则，测试是否愿意为可导出通知付费"}
    if "reminder" in ql:
        return {"task":"生成发票催款提醒，并根据逾期天数选择不同语气和跟进节奏", "artifact":"催款邮件/短信 + 逾期天数计算 + 跟进日历", "test":"测试用户是否愿意为品牌化导出、批量提醒或会计工具集成付费"}
    if "payment terms" in ql:
        return {"task":"帮助小企业选择/解释 Net 7、Net 15、Net 30 等付款条款，并计算现金流影响", "artifact":"付款条款比较器 + 推荐条款 + 合同句子模板", "test":"测试用户是否点击下载合同条款模板或咨询付款政策"}
    if "estimate" in ql:
        return {"task":"把报价估算转成专业 invoice/estimate 输出，减少手工计算和格式错误", "artifact":"报价估算器 + 可导出 estimate/invoice PDF + 项目行模板", "test":"测试用户是否为 PDF 导出、模板包或会计软件导入付费"}
    return {"task":f"解决 `{keyword_query}` 背后的单一任务", "artifact":"单页工具/模板 + 可导出结果", "test":"测试用户是否愿意为导出、模板包或定制服务付费"}

def _keyword_specific_mvp(keyword_query: str, biz: dict, verdict: str, reason: str) -> str:
    q = keyword_query.strip()
    detail = _keyword_task_detail(q)
    if verdict == "Reject":
        return f"{reason}\n\n不建议推进：`{q}` 当前不应作为独立机会执行。下一步只做证据补充：重新检查搜索意图、换更具体的长尾词、确认是否有真实付费场景；证据不足前不要做 MVP。"
    if verdict == "Watch":
        return f"{reason}\n\n待验证假设：围绕 `{q}` 做一个最小验证页，不先完整开发产品。\n\n要验证的具体任务：{detail['task']}。\n\n最小交付：{detail['artifact']}。\n\n验证动作：{detail['test']}；同时记录点击、留资或回复。如果没有明确转化，再降级或换词。"
    return f"{reason}\n\n执行型 MVP：围绕 `{q}` 做一个单页工具/模板，只解决这个具体任务：{detail['task']}。\n\n核心交付：{detail['artifact']}。\n\n变现路径：{biz['revenue_path']}\n\n定价测试：{biz['pricing']}\n\n获客入口：{biz['gtm']}\n\n第一笔钱测试：{detail['test']}。\n\n关键假设：{biz['key_assumption']}"

def _verdict_rank(v: str) -> int:
    return {"Reject": 0, "Watch": 1, "Action": 2}.get(v, 1)

def _safe_verdict(llm_v: str, rule_v: str) -> str:
    v = str(llm_v or "").strip().title()
    if v not in {"Action", "Watch", "Reject"}:
        return rule_v
    # LLM may be more conservative than rules, but must not upgrade evidence.
    return v if _verdict_rank(v) <= _verdict_rank(rule_v) else rule_v

def _llm_opportunity_analysis(db: Session, keyword: models.Keyword, serp: list[models.SerpResult], comps: list[models.CompetitorPage], socials: list[models.SocialEvidence], metrics: dict, rule_verdict: str, rule_reason: str) -> dict | None:
    if (setting(db, "LLM_CARD_ANALYSIS_ENABLED") or "true").lower() not in {"1","true","yes","on"}:
        return None
    system = """你是 Nero 的 SEO 需求词机会分析器。你的职责不是套模板，而是基于真实搜索证据判断一个关键词是否值得推进为可验证商业机会。

核心方法融合 Four-Find 与两篇找词文章：
- Four-Find 负责扩词路径：词找词、词找站、站找词、站找站。
- 文章方法负责判断：搜索词是否代表真实需求、新词/老词属性、Google Trends/国家分布、搜索量/CPC/KD、SERP 是否可打、是否适合快速做 SEO 工具页。

必须遵守：
1. 中文输出。英文原始标题/关键词可以保留，但解释必须中文。
2. 不能编造证据，只能使用输入里的关键词、SERP、竞品、社媒证据；如果缺少 volume/CPC/KD/趋势/国家分布，就明确写“需要补证据”，不要假设。
3. 每张卡必须针对该关键词的具体搜索任务，不允许输出泛泛的“做一个工具/模板”。
4. 必须判断该词属于哪类：新词/上升词/老词/常青词/未知。没有趋势证据时写“未知，需要 Google Trends/SEO 工具补证”。
5. 必须判断是否适合 SEO 工具页：calculator/template/checker/generator/converter 等轻量页面优先；若只是泛信息词或品牌错配，应降级。
6. Action/Watch/Reject 必须和证据强度一致：
   - Action：搜索意图清楚、SERP 有缺口、竞品/现有结果弱、能定义很小的付费/广告/联盟验证，并且没有明显 SEO 指标缺口。
   - Watch：方向可能有价值，但缺搜索量/CPC/KD/趋势/国家/付费验证等关键证据。
   - Reject：搜索入口错、意图混乱、强竞品过多、缺口弱或无法定义付费验证。
7. Reject 不能包装成机会；只能写否决原因和需要补什么证据。
8. 输出必须是严格 JSON，不要 Markdown，不要代码块。"""
    evidence = {
        "keyword": keyword.query,
        "intent": keyword.intent,
        "rule_verdict": rule_verdict,
        "rule_reason": rule_reason,
        "metrics": metrics,
        "serp_top": [{"rank": s.rank, "title": s.title, "domain": s.domain, "url": s.url, "snippet": s.snippet[:500], "gap_tags": json.loads(s.gap_tags or "[]"), "weakness_score": s.weakness_score} for s in serp[:10]],
        "competitors": [{"domain": c.domain, "title": c.title, "url": c.url, "weakness_tags": json.loads(c.weakness_tags or "[]"), "excerpt": c.content_excerpt[:500]} for c in comps[:6]],
        "social_evidence": [{"platform": x.platform, "title": x.title, "url": x.url, "snippet": x.snippet[:500], "pain_tags": json.loads(x.pain_tags or "[]")} for x in socials[:6]],
    }
    user = """请基于以下证据生成一张机会分析卡。输出 JSON schema：
{
  "title": "中文机会标题，必须包含关键词的具体任务",
  "verdict": "Action|Watch|Reject",
  "verdict_reason": "为什么是这个判断，引用输入中的关键指标/证据",
  "business_type": "机会类型/变现类型，中文",
  "icp": "目标用户，中文且具体",
  "pain": "痛点，中文且具体",
  "pay_trigger": "什么情况下愿意付费",
  "wedge": "切入点，必须具体到该关键词任务",
  "mvp_plan": "Action 写执行型 MVP；Watch 写待验证假设；Reject 写不建议推进和补证据方向。中文，分段也可以但不要 Markdown",
  "revenue_path": "收入路径，中文",
  "pricing": "定价测试，中文",
  "gtm": "获客入口，中文",
  "first_sale_test": ["第一步", "第二步", "第三步"],
  "key_assumption": "关键假设",
  "risks": ["风险1", "风险2"],
  "keyword_type": "new|rising|old|evergreen|unknown",
  "seo_fit": "high|medium|low|unknown",
  "missing_evidence": ["缺少搜索量", "缺少CPC", "缺少KD", "缺少国家分布"],
  "commercial_score": 0.0到1.0
}

证据：
""" + json.dumps(evidence, ensure_ascii=False)
    obj = _llm_json(db, system, user, temperature=0.15)
    if not obj:
        return None
    required=["title","verdict","verdict_reason","business_type","icp","pain","pay_trigger","wedge","mvp_plan","revenue_path","pricing","gtm","first_sale_test","key_assumption","risks"]
    if not all(k in obj for k in required):
        return None
    return obj

def make_card(db: Session, keyword: models.Keyword) -> models.OpportunityCard:
    existing_reviewed = db.query(models.OpportunityCard).filter_by(keyword_id=keyword.id).filter(models.OpportunityCard.feedback_label.in_(["Adopted","Action","Watch","Reject","Block"])).order_by(models.OpportunityCard.created_at.desc(), models.OpportunityCard.id.desc()).first()
    if existing_reviewed:
        # Human review is authoritative. Automatic rechecks may refresh future
        # unreviewed candidates, but must never overwrite a reviewed card's
        # verdict/feedback. This prevents Watch/Reject cards from reappearing as
        # Action after a scheduled run.
        existing_reviewed.verdict = existing_reviewed.feedback_label
        keyword.status = existing_reviewed.feedback_label.lower()
        keyword.score = existing_reviewed.score or keyword.score
        db.commit(); db.refresh(existing_reviewed); return existing_reviewed
    noise_reason = keyword_noise_reason(keyword.query, keyword.source)
    if noise_reason:
        keyword.status = "rejected"
        keyword.intent = f"noise:{noise_reason}"[:80]
        keyword.score = 0.0
        existing = db.query(models.OpportunityCard).filter_by(keyword_id=keyword.id).order_by(models.OpportunityCard.created_at.desc(), models.OpportunityCard.id.desc()).first()
        evidence=[{"type":"business","business_type":"rejected_noise","icp":"-","pain":"-","pay_trigger":"-","wedge":"-","commercial_mvp":"-","revenue_path":"-","pricing":"-","gtm":"-","first_sale_test":[],"key_assumption":"-","commercial_score":0.0,"go_no_go":"No-Go","verdict_reason":f"拒绝：关键词被识别为噪音（{noise_reason}），不生成机会卡。","analysis_source":"rules_noise_gate"}]
        if existing:
            existing.verdict="Reject"; existing.score=0.0; existing.mvp_score=0.0; existing.monetization_score=0.0; existing.mvp_plan=f"关键词噪音：{noise_reason}。不要推进。"; existing.evidence_json=json.dumps(evidence,ensure_ascii=False); existing.risks=json.dumps(["关键词来源噪音"],ensure_ascii=False)
            card=existing
        else:
            card=models.OpportunityCard(keyword_id=keyword.id,title=f"拒绝：{keyword.query}", verdict="Reject", score=0.0, demand_score=0.0, serp_gap_score=0.0, competitor_weakness_score=0.0, mvp_score=0.0, monetization_score=0.0, monetization_type="rejected_noise", mvp_plan=f"关键词噪音：{noise_reason}。不要推进。", evidence_json=json.dumps(evidence,ensure_ascii=False), risks=json.dumps(["关键词来源噪音"],ensure_ascii=False))
            db.add(card)
        db.commit(); db.refresh(card); return card
    duplicate = find_duplicate_card(db, keyword)
    if duplicate:
        return append_duplicate_evidence(db, duplicate, keyword, similarity_note="Auto-detected duplicate/variant; merged into this opportunity evidence chain.")
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
    if verdict == "Action" and any(w in keyword.query.lower() for w in ["api", "shopify", "woocommerce", "sales tax"]):
        # API/platform tax queries often look commercially strong but SERP is
        # dominated by docs, vendors, and setup guides. Keep as Watch until a
        # concrete paid workflow / first-sale test is validated.
        verdict = "Watch"
    reason = _zh_verdict_reason(verdict, total, gap, strong_count, relevant_count, has_social, require_social, mismatch_count)
    risks=[]
    if strong_count>3: risks.append("SERP 强品牌过多，切入难度高")
    if len(socials)==0 and require_social: risks.append("缺少社媒痛点旁证")
    if mismatch_count >= max(2, len(serp)//2): risks.append("SERP 查询意图不匹配，搜索入口不可靠")
    if gap<.5: risks.append("SERP 缺口不明显")
    metrics={"total_score":total,"demand_score":round(demand,2),"serp_gap_score":round(gap,2),"competitor_weakness_score":round(comp,2),"commercial_score":commercial,"monetization_score":mscore,"strong_count":strong_count,"mismatch_count":mismatch_count,"relevant_count":relevant_count,"has_social":has_social,"require_social":require_social}
    llm = _llm_opportunity_analysis(db, keyword, serp, comps, socials, metrics, verdict, reason)
    if llm:
        verdict = _safe_verdict(llm.get("verdict"), verdict)
        reason = str(llm.get("verdict_reason") or reason)
        commercial = max(0.0, min(1.0, float(llm.get("commercial_score") or commercial)))
        biz.update({
            "business_type": str(llm.get("business_type") or biz.get("business_type")),
            "icp": str(llm.get("icp") or biz.get("icp")),
            "pain": str(llm.get("pain") or biz.get("pain")),
            "pay_trigger": str(llm.get("pay_trigger") or biz.get("pay_trigger")),
            "wedge": str(llm.get("wedge") or biz.get("wedge")),
            "commercial_mvp": str(llm.get("mvp_plan") or biz.get("commercial_mvp")),
            "revenue_path": str(llm.get("revenue_path") or biz.get("revenue_path")),
            "pricing": str(llm.get("pricing") or biz.get("pricing")),
            "gtm": str(llm.get("gtm") or biz.get("gtm")),
            "first_sale_test": llm.get("first_sale_test") if isinstance(llm.get("first_sale_test"), list) else biz.get("first_sale_test"),
            "key_assumption": str(llm.get("key_assumption") or biz.get("key_assumption")),
            "commercial_score": commercial,
            "keyword_type": str(llm.get("keyword_type") or "unknown"),
            "seo_fit": str(llm.get("seo_fit") or "unknown"),
            "missing_evidence": llm.get("missing_evidence") if isinstance(llm.get("missing_evidence"), list) else [],
            "analysis_source": "llm",
        })
        plan = str(llm.get("mvp_plan") or _keyword_specific_mvp(keyword.query, biz, verdict, reason))
        title = str(llm.get("title") or f"{keyword.query} 机会")
        llm_risks = llm.get("risks") if isinstance(llm.get("risks"), list) else []
        risks = [str(x) for x in llm_risks if str(x).strip()] or risks
        mtype = str(llm.get("business_type") or mtype)
    else:
        biz["analysis_source"] = "rules_fallback"
        plan = _keyword_specific_mvp(keyword.query, biz, verdict, reason)
        title = f"{keyword.query} 机会"
    biz["verdict_reason"] = reason
    evidence = [biz] + [{"type":"serp","url":s.url,"title":s.title,"tags":json.loads(s.gap_tags or "[]")} for s in serp[:5]] + [{"type":x.platform,"url":x.url,"title":x.title} for x in socials[:4]]
    existing = db.query(models.OpportunityCard).filter_by(keyword_id=keyword.id).order_by(models.OpportunityCard.created_at.desc(), models.OpportunityCard.id.desc()).first()
    if existing:
        card = existing
        card.title = title
        card.verdict = existing.feedback_label if existing.feedback_label in {"Adopted", "Action", "Watch", "Reject", "Block"} else verdict
        card.score = total
        card.demand_score = round(demand,2)
        card.serp_gap_score = round(gap,2)
        card.competitor_weakness_score = round(comp,2)
        card.mvp_score = commercial
        card.monetization_score = mscore
        card.monetization_type = mtype
        card.mvp_plan = plan
        card.evidence_json = json.dumps(evidence,ensure_ascii=False)
        card.risks = json.dumps(risks,ensure_ascii=False)
    else:
        card=models.OpportunityCard(keyword_id=keyword.id,title=title, verdict=verdict, score=total, demand_score=round(demand,2), serp_gap_score=round(gap,2), competitor_weakness_score=round(comp,2), mvp_score=commercial, monetization_score=mscore, monetization_type=mtype, mvp_plan=plan, evidence_json=json.dumps(evidence,ensure_ascii=False), risks=json.dumps(risks,ensure_ascii=False))
        db.add(card)
    keyword.score=total; keyword.status=card.verdict.lower(); db.commit(); db.refresh(card); return card

def reanalyze_card_business(db: Session, card: models.OpportunityCard) -> models.OpportunityCard:
    """Refresh business analysis for an existing card without changing human state.

    Used when a card has generic rules_fallback/restored content. Preserves
    feedback_label/verdict but replaces the business evidence block with LLM
    output when available, otherwise a keyword-specific fallback clearly marked.
    """
    keyword=db.get(models.Keyword, card.keyword_id)
    if not keyword:
        return card
    serp=db.query(models.SerpResult).filter_by(keyword_id=keyword.id).all() or run_serp(db, keyword)
    comps=analyze_competitors(db, keyword)
    socials=collect_social(db, keyword)
    gap=sum(s.weakness_score for s in serp[:10]) / max(1, len(serp[:10]))
    strong_count=sum(1 for s in serp if "strong_brand" in (s.gap_tags or ""))
    mismatch_count=sum(1 for s in serp if "query_mismatch" in (s.gap_tags or ""))
    relevant_count=max(0, len(serp)-mismatch_count)
    forum_count=sum(1 for s in serp if "forum_heavy" in (s.gap_tags or ""))
    demand=min(1.0, 0.30 + 0.06*relevant_count + 0.08*len(socials))
    comp=min(1.0, 0.35 + 0.1*len(comps) + 0.08*forum_count - 0.06*strong_count)
    mtype, mscore=monetization(keyword.query, keyword.intent)
    biz=business_profile(keyword.query, keyword.intent, mtype)
    commercial=float(biz.get("commercial_score",0.55))
    rule_verdict=card.feedback_label or card.verdict or "Watch"
    reason=_zh_verdict_reason("Watch" if rule_verdict=="Adopted" else rule_verdict, float(card.score or 0), gap, strong_count, relevant_count, len(socials)>0, (setting(db,"REQUIRE_SOCIAL_FOR_ACTION") or "true").lower() in {"1","true","yes","on"}, mismatch_count)
    metrics={"total_score":card.score,"demand_score":round(demand,2),"serp_gap_score":round(gap,2),"competitor_weakness_score":round(comp,2),"commercial_score":commercial,"monetization_score":mscore,"strong_count":strong_count,"mismatch_count":mismatch_count,"relevant_count":relevant_count,"has_social":len(socials)>0}
    llm=_llm_opportunity_analysis(db, keyword, serp, comps, socials, metrics, "Watch" if rule_verdict=="Adopted" else rule_verdict, reason)
    if llm:
        commercial=max(0.0,min(1.0,float(llm.get("commercial_score") or commercial)))
        biz.update({"business_type":str(llm.get("business_type") or biz.get("business_type")),"icp":str(llm.get("icp") or biz.get("icp")),"pain":str(llm.get("pain") or biz.get("pain")),"pay_trigger":str(llm.get("pay_trigger") or biz.get("pay_trigger")),"wedge":str(llm.get("wedge") or biz.get("wedge")),"commercial_mvp":str(llm.get("mvp_plan") or biz.get("commercial_mvp")),"revenue_path":str(llm.get("revenue_path") or biz.get("revenue_path")),"pricing":str(llm.get("pricing") or biz.get("pricing")),"gtm":str(llm.get("gtm") or biz.get("gtm")),"first_sale_test":llm.get("first_sale_test") if isinstance(llm.get("first_sale_test"),list) else biz.get("first_sale_test"),"key_assumption":str(llm.get("key_assumption") or biz.get("key_assumption")),"commercial_score":commercial,"keyword_type":str(llm.get("keyword_type") or "unknown"),"seo_fit":str(llm.get("seo_fit") or "unknown"),"missing_evidence":llm.get("missing_evidence") if isinstance(llm.get("missing_evidence"),list) else [],"analysis_source":"llm_reanalysis"})
        card.title=str(llm.get("title") or card.title)
        card.mvp_plan=str(llm.get("mvp_plan") or card.mvp_plan)
        if isinstance(llm.get("risks"),list): card.risks=json.dumps([str(x) for x in llm.get("risks")],ensure_ascii=False)
        card.monetization_type=str(llm.get("business_type") or card.monetization_type)
    else:
        detail=_keyword_task_detail(keyword.query)
        biz.update({"analysis_source":"specific_rules_fallback_no_llm","commercial_mvp":_keyword_specific_mvp(keyword.query,biz,"Watch" if rule_verdict=="Adopted" else rule_verdict,reason),"wedge":detail["artifact"],"first_sale_test":[detail["test"]],"missing_evidence":["LLM 分析未返回有效 JSON，需要人工/模型重跑","需要补搜索量/CPC/KD/趋势/国家分布"]})
        card.mvp_plan=biz["commercial_mvp"]
    biz["type"]="business"; biz["verdict_reason"]=str((llm or {}).get("verdict_reason") or reason)
    try:
        ev=json.loads(card.evidence_json or "[]")
        if not isinstance(ev,list): ev=[ev]
    except Exception: ev=[]
    ev=[x for x in ev if not (isinstance(x,dict) and x.get("type")=="business")]
    card.evidence_json=json.dumps([biz]+ev,ensure_ascii=False)
    db.merge(card); db.commit(); db.refresh(card); return card

def select_old_keywords_for_recheck(db: Session, limit: int = 4) -> list[models.Keyword]:
    """Pick existing keywords for periodic re-evaluation.

    Old keywords matter: SERPs change, Watch can become Action, and Reject can
    become valid if the query or provider behavior improves. Prefer keywords
    that already have cards and are not currently hard SERP-rejected.
    """
    if limit <= 0:
        return []
    rows = (
        db.query(models.Keyword)
        .join(models.OpportunityCard, models.OpportunityCard.keyword_id == models.Keyword.id)
        .filter(~models.Keyword.status.in_(["serp_reject", "rewrite_exhausted", "rejected", "reject", "block", "duplicate"]))
        .order_by(models.Keyword.status.desc(), models.OpportunityCard.created_at.asc(), models.Keyword.id.asc())
        .limit(limit)
        .all()
    )
    seen=set(); out=[]
    for kw in rows:
        if kw.id not in seen:
            out.append(kw); seen.add(kw.id)
    return out

def select_collector_keywords(db: Session, limit: int = 8) -> list[models.Keyword]:
    if limit <= 0:
        return []
    return (
        db.query(models.Keyword)
        .filter(models.Keyword.source.like("collector:%"))
        .filter(~models.Keyword.status.in_(["rejected", "reject", "block", "duplicate", "serp_reject", "rewrite_exhausted", "imported"]))
        .order_by(models.Keyword.score.desc(), models.Keyword.created_at.desc())
        .limit(limit)
        .all()
    )

def _repair_action_key(action: dict) -> str:
    return f"{action.get('action','')}:{action.get('source') or ''}"

def repair_strategy_stats(db: Session, limit: int = 80) -> dict:
    rows=db.query(models.RunHistory).filter(models.RunHistory.kind=="repair").order_by(models.RunHistory.started_at.desc()).limit(limit).all()
    stats={}
    for row in rows:
        summary=_parse_run_summary(row)
        key=f"{summary.get('action','')}:{summary.get('source') or ''}"
        if not summary.get("action"):
            continue
        entry=stats.setdefault(key,{"action":summary.get("action"),"source":summary.get("source"),"runs":0,"improved":0,"neutral":0,"regressed":0,"rolled_back":0,"pending":0,"delta_sum":0.0,"priority":1.0,"last_experiment_at":None})
        if not entry.get("last_experiment_at") or (row.started_at and row.started_at.isoformat() > entry.get("last_experiment_at")):
            entry["last_experiment_at"] = row.started_at.isoformat() if row.started_at else None
        effect=evaluate_repair_effect(db,row)
        status=effect.get("status") or "unknown"
        entry["runs"] += 1
        if status in entry:
            entry[status] += 1
        if status == "rolled_back":
            entry["rolled_back"] += 1
        try: entry["delta_sum"] += float(effect.get("delta") or 0)
        except Exception: pass
    for key,entry in stats.items():
        completed=max(1, entry["improved"]+entry["neutral"]+entry["regressed"])
        avg_delta=entry["delta_sum"]/completed
        priority=1.0 + entry["improved"]*0.25 - entry["regressed"]*0.35 - entry["rolled_back"]*0.45 + max(-0.4, min(0.4, avg_delta/25))
        entry["avg_delta"]=round(avg_delta,2)
        entry["priority"]=round(max(0.1,min(2.5,priority)),2)
        entry["hide"]=entry["regressed"]>=2 and entry["improved"]==0
    return stats

def _cooldown_hours_from_stats(strategy_stats: dict) -> float:
    raw=(strategy_stats or {}).get("__cooldown_hours", 24)
    try: return max(0.0, float(raw))
    except Exception: return 24.0

def _is_repair_in_cooldown(st: dict, cooldown_hours: float) -> tuple[bool, str | None]:
    if cooldown_hours <= 0 or not st.get("last_experiment_at"):
        return False, None
    try:
        last=datetime.fromisoformat(st["last_experiment_at"])
        until=last + timedelta(hours=cooldown_hours)
        if datetime.utcnow() < until:
            return True, until.isoformat(timespec="seconds")
    except Exception:
        return False, None
    return False, None

def rank_repair_actions(actions: list[dict], strategy_stats: dict | None = None) -> list[dict]:
    ranked, _ = rank_repair_actions_with_meta(actions, strategy_stats)
    return ranked

def rank_repair_actions_with_meta(actions: list[dict], strategy_stats: dict | None = None) -> tuple[list[dict], dict]:
    strategy_stats=strategy_stats or {}
    cooldown_hours=_cooldown_hours_from_stats(strategy_stats)
    out=[]; seen=set(); meta={"total_candidates":0,"deduped_candidates":0,"hidden":0,"cooldown":0,"cooldown_until":None,"cooldown_hours":cooldown_hours}
    for a in actions:
        meta["total_candidates"] += 1
        key=_repair_action_key(a)
        if key in seen:
            continue
        seen.add(key)
        meta["deduped_candidates"] += 1
        st=strategy_stats.get(key) or strategy_stats.get(f"{a.get('action','')}:" ) or {}
        if st.get("hide"):
            meta["hidden"] += 1
            continue
        in_cd, until = _is_repair_in_cooldown(st, cooldown_hours)
        if in_cd:
            meta["cooldown"] += 1
            if until and (not meta["cooldown_until"] or until < meta["cooldown_until"]):
                meta["cooldown_until"] = until
            continue
        enriched={**a,"strategy":st or None,"priority":float(st.get("priority",1.0) if st else 1.0)}
        if st:
            enriched["label"] = f"{a.get('label')} · p{enriched['priority']:.1f}"
        out.append(enriched)
    ranked=sorted(out, key=lambda x:x.get("priority",1.0), reverse=True)
    meta["available"] = len(ranked)
    return ranked, meta

def annotate_manual_repair_actions(actions: list[dict], strategy_stats: dict | None = None) -> list[dict]:
    strategy_stats=strategy_stats or {}
    cooldown_hours=_cooldown_hours_from_stats(strategy_stats)
    out=[]; seen=set()
    for a in actions:
        key=_repair_action_key(a)
        if key in seen:
            continue
        seen.add(key)
        st=strategy_stats.get(key) or strategy_stats.get(f"{a.get('action','')}:" ) or {}
        in_cd, until = _is_repair_in_cooldown(st, cooldown_hours)
        label=a.get("label") or a.get("action")
        flags=[]
        if in_cd: flags.append("cooldown")
        if st.get("hide"): flags.append("history_hidden")
        enriched={**a,"strategy":st or None,"priority":float(st.get("priority",1.0) if st else 1.0),"manual_flags":flags,"cooldown_until":until}
        if flags:
            enriched["label"] = f"{label} · {'/'.join(flags)}"
        out.append(enriched)
    return sorted(out, key=lambda x:x.get("priority",1.0), reverse=True)

def diagnose_quality_report(report: dict, db: Session | None = None) -> dict:
    """Heuristic diagnosis for one run's quality funnel.

    Keep this deterministic: it should explain where the pipeline leaked without
    requiring an LLM call or inventing hidden causes.
    """
    f = report.get("funnel") or {}
    collector = report.get("collector") or {}
    issues=[]; actions=[]; repair_actions=[]
    def n(key):
        try: return int(f.get(key) or 0)
        except Exception: return 0
    seen=n("collector_seen"); saved=n("collector_saved"); scanned=n("clean_scanned")
    clean_rejected=n("clean_rejected"); imported=n("imported_keywords")
    processed=n("keywords_processed"); serp_rejected=n("serp_rejected"); duplicates=n("duplicates"); cards=n("cards"); action=n("action"); watch=n("watch")
    errors=[]
    for row in collector.get("by_source") or []:
        if int(row.get("errors") or 0) > 0:
            errors.append(row)
    if errors:
        issues.append({"severity":"warning","code":"collector_errors","title":"部分采集器有错误","detail":f"{len(errors)} 个 collector/source 报错。"})
        actions.append("先检查 Collector 产出表里的 errors；如果集中在付费/外部 API，降低该 source 权重或检查 key/quota。")
        for row in errors[:3]:
            if row.get("source"):
                repair_actions.append({"id":f"lower_weight:{row['source']}","label":f"降低 {row['source']} 权重","action":"lower_source_weight","source":row.get("source"),"safety":"可逆：仅调整内部权重"})
    if seen == 0:
        issues.append({"severity":"critical","code":"no_collector_input","title":"采集层没有输入","detail":"collector_seen=0，本轮没有拿到任何候选原料。"})
        actions.append("检查 seeds/domains 是否为空、搜索源是否可用；先运行 Settings 里的搜索测试。")
        repair_actions.append({"id":"add_commercial_seeds","label":"补充默认商业 seeds","action":"add_commercial_seeds","safety":"可逆：只追加内部 seeds"})
    elif saved == 0:
        issues.append({"severity":"info","code":"no_new_collector_candidates","title":"采集层本轮无新增候选","detail":f"seen={seen}，saved=0。强过滤已拦截重复/噪音结果。"})
        actions.append("如果连续多轮 saved=0，再补充新的商业化 seeds；单轮 0 saved 不代表流程故障。")
    elif saved / max(1, seen) < 0.08:
        issues.append({"severity":"warning","code":"low_candidate_save_rate","title":"采集→候选保存率低","detail":f"saved/seen={saved}/{seen}。"})
        actions.append("当前采集结果大多无法转成关键词；增加更商业化 seeds，或降低低产 collector 预算。")
        repair_actions.append({"id":"add_commercial_seeds","label":"追加商业化 seed 模板","action":"add_commercial_seeds","safety":"可逆：只追加内部 seeds"})
    if scanned and clean_rejected / max(1, scanned) > 0.65:
        issues.append({"severity":"warning","code":"high_clean_reject_rate","title":"清洗拒绝率过高","detail":f"clean_rejected/scanned={clean_rejected}/{scanned}。"})
        actions.append("候选噪音偏多；查看 duplicate/noise 原因，减少 generic seeds（best/free/online 类）并提高强商业词比例。")
        repair_actions.append({"id":"prune_generic_seeds","label":"移除泛噪音 seeds","action":"prune_generic_seeds","safety":"可逆：只改内部 seed 列表"})
    if saved > 0 and imported == 0:
        issues.append({"severity":"critical","code":"no_keyword_import","title":"候选没有导入关键词流","detail":"有候选保存，但 imported_keywords=0。"})
        actions.append("检查候选是否都被去重或已存在；如果都已存在，应提高 recheck 预算或拓展新 seeds。")
        repair_actions.append({"id":"increase_import_limit","label":"提高候选导入额度","action":"increase_import_limit","safety":"可逆：只改内部 limit"})
    if processed > 0 and serp_rejected / max(1, processed) > 0.7:
        top_reason = ""
        reasons = report.get("serp_gate_reasons") or {}
        if reasons:
            top_reason = sorted(reasons.items(), key=lambda x:x[1], reverse=True)[0][0]
        issues.append({"severity":"critical","code":"high_serp_reject_rate","title":"SERP Gate 拒绝率过高","detail":f"serp_rejected/processed={serp_rejected}/{processed}" + (f"，主因 {top_reason}" if top_reason else "。")})
        if top_reason == "no_commercial_serp_signal":
            actions.append("关键词商业意图不足；优先加入 calculator/template/software/pricing/integration 等商业后缀，并降低泛信息源预算。")
            repair_actions.append({"id":"add_commercial_seeds","label":"补充商业意图 seeds","action":"add_commercial_seeds","safety":"可逆：只追加内部 seeds"})
        elif top_reason == "informational_or_dictionary_serp":
            actions.append("搜索结果偏定义/百科；改写 seed 为具体工作流或垂直行业任务，避免单泛词。")
            repair_actions.append({"id":"prune_generic_seeds","label":"移除泛信息 seeds","action":"prune_generic_seeds","safety":"可逆：只改内部 seed 列表"})
        else:
            actions.append("查看 SERP Gate examples；如果明显误杀，调整 query variants 或接入更稳定 SERP provider。")
        repair_actions.append({"id":"enable_rewrite_recovery","label":"开启 SERP Reject 改写恢复","action":"enable_rewrite_recovery","safety":"可逆：只改内部开关"})
    if processed > 0 and cards == 0 and serp_rejected == 0:
        if duplicates >= processed:
            issues.append({"severity":"info","code":"all_keywords_duplicate","title":"本轮关键词都被去重拦截","detail":f"duplicates/processed={duplicates}/{processed}，未生成新卡是因为已有相近机会卡。"})
            actions.append("减少重复 seeds/root_combo 预算，增加新的垂直种子；无需检查 LLM。")
            repair_actions.append({"id":"prune_generic_seeds","label":"移除泛重复 seeds","action":"prune_generic_seeds","safety":"可逆：只改内部 seed 列表"})
        else:
            issues.append({"severity":"warning","code":"no_cards_without_serp_reject","title":"关键词处理了但没有卡片","detail":"SERP 没被拒绝，但 cards=0。"})
            actions.append("检查 make_card / LLM 配置与日志；这通常不是采集问题。")
    if cards > 0 and action == 0 and watch == 0:
        issues.append({"severity":"info","code":"cards_low_quality","title":"生成了卡片但没有 Action/Watch","detail":f"cards={cards}，Action/Watch=0。"})
        actions.append("说明机会质量不足；把 Reject 来源反馈回 collector，系统会自动降权。")
    if not issues:
        issues.append({"severity":"ok","code":"healthy","title":"本轮漏斗健康","detail":"未发现明显阻断点。"})
        actions.append("继续复核 Watch/Action 卡；反馈会自动影响下一轮采集预算。")
    severity_order={"ok":0,"info":1,"warning":2,"critical":3}
    severity=max((i["severity"] for i in issues), key=lambda x: severity_order.get(x,0))
    next_action=actions[0] if actions else "继续观察下一轮。"
    strategy_stats=repair_strategy_stats(db) if db is not None else {}
    if db is not None:
        try: strategy_stats["__cooldown_hours"] = float(setting(db, "REPAIR_EXPERIMENT_COOLDOWN_HOURS") or "24")
        except Exception: strategy_stats["__cooldown_hours"] = 24
    ranked_repairs, repair_meta=rank_repair_actions_with_meta(repair_actions, strategy_stats)
    manual_repairs=annotate_manual_repair_actions(repair_actions, strategy_stats)
    fallback = None
    if repair_actions and not ranked_repairs:
        if repair_meta.get("cooldown") and repair_meta.get("cooldown") >= repair_meta.get("deduped_candidates",0) - repair_meta.get("hidden",0):
            fallback = f"暂无新的推荐实验：候选修复动作都在 {repair_meta.get('cooldown_hours')} 小时冷却期内。"
        elif repair_meta.get("hidden"):
            fallback = "暂无新的推荐实验：候选修复动作历史效果较差，已被暂时隐藏。"
        else:
            fallback = "暂无新的推荐实验；可以等待下一轮数据或展开其它修复动作手动处理。"
    return {"severity":severity,"issues":issues,"recommended_actions":actions[:6],"repair_actions":ranked_repairs[:6],"manual_repair_actions":manual_repairs[:8],"recommended_experiment":ranked_repairs[0] if ranked_repairs else None,"repair_recommendation_meta":repair_meta,"repair_recommendation_fallback":fallback,"repair_strategy_stats":strategy_stats,"next_action":next_action}

def _setting_list(db: Session, key: str) -> list[str]:
    return [x.strip() for x in re.split(r"[\n,]+", setting(db, key) or "") if x.strip()]

def _save_setting_list(db: Session, key: str, values: list[str], sep: str = ",") -> None:
    row=db.get(models.Setting, key) or models.Setting(key=key, value="", secret=False)
    seen=[]
    for v in values:
        v=(v or "").strip()
        if v and v not in seen:
            seen.append(v)
    row.value=sep.join(seen[:100])
    row.secret=False
    db.merge(row)

def _record_repair_audit(db: Session, payload: dict) -> models.RunHistory:
    row=models.RunHistory(kind="repair", status="ok", summary=json.dumps(payload, ensure_ascii=False), finished_at=datetime.utcnow())
    db.add(row)
    db.commit(); db.refresh(row)
    return row

def _parse_run_summary(row: models.RunHistory | None) -> dict:
    if not row or not row.summary:
        return {}
    try:
        return json.loads(row.summary or "{}") if row.summary.startswith("{") else {"raw": row.summary}
    except Exception:
        return {"raw": row.summary}

def _latest_daily_with_quality(db: Session, before: datetime | None = None, after: datetime | None = None) -> models.RunHistory | None:
    q=db.query(models.RunHistory).filter(models.RunHistory.kind=="daily", models.RunHistory.status=="ok")
    if before is not None:
        q=q.filter(models.RunHistory.started_at <= before)
    if after is not None:
        q=q.filter(models.RunHistory.started_at > after)
    rows=q.order_by(models.RunHistory.started_at.desc() if before is not None else models.RunHistory.started_at.asc()).limit(25).all()
    for row in rows:
        summary=_parse_run_summary(row)
        if isinstance(summary.get("quality_report"), dict):
            return row
    return None

def _quality_health_score(report: dict) -> dict:
    f=(report or {}).get("funnel") or {}
    def n(key):
        try: return float(f.get(key) or 0)
        except Exception: return 0.0
    seen=n("collector_seen"); saved=n("collector_saved"); scanned=n("clean_scanned"); clean_rejected=n("clean_rejected")
    processed=n("keywords_processed"); serp_rejected=n("serp_rejected"); duplicates=n("duplicates"); cards=n("cards"); action=n("action"); watch=n("watch")
    save_rate=saved/max(1.0,seen)
    clean_reject_rate=clean_rejected/max(1.0,scanned)
    serp_reject_rate=serp_rejected/max(1.0,processed)
    card_rate=cards/max(1.0,processed)
    useful_rate=(action+watch)/max(1.0,cards)
    score=50
    score += min(15, save_rate*60)
    score += min(15, card_rate*40)
    score += min(15, useful_rate*25)
    score -= min(25, clean_reject_rate*30)
    score -= min(35, serp_reject_rate*45)
    if action > 0: score += 8
    elif watch > 0: score += 3
    return {"score": round(max(0,min(100,score)),1), "save_rate":round(save_rate,3), "clean_reject_rate":round(clean_reject_rate,3), "serp_reject_rate":round(serp_reject_rate,3), "card_rate":round(card_rate,3), "useful_rate":round(useful_rate,3), "funnel": f}

def evaluate_repair_effect(db: Session, repair_row: models.RunHistory) -> dict:
    summary=_parse_run_summary(repair_row)
    if summary.get("rolled_back"):
        return {"status":"rolled_back", "note":"repair 已回滚，不再评估效果。"}
    baseline=summary.get("baseline") or {}
    baseline_report=baseline.get("quality_report") if isinstance(baseline, dict) else None
    if not baseline_report:
        before_row=_latest_daily_with_quality(db, before=repair_row.started_at)
        before_summary=_parse_run_summary(before_row)
        baseline_report=before_summary.get("quality_report")
        if before_row and baseline_report:
            baseline={"run_id":before_row.id,"started_at":before_row.started_at.isoformat(),"quality_report":baseline_report}
    if not baseline_report:
        return {"status":"no_baseline", "note":"repair 前没有可对比的 quality_report。"}
    after_row=_latest_daily_with_quality(db, after=repair_row.started_at)
    if not after_row:
        return {"status":"pending", "note":"等待 repair 后第一轮 daily run 完成。", "before": _quality_health_score(baseline_report), "baseline_run_id": baseline.get("run_id")}
    after_summary=_parse_run_summary(after_row)
    after_report=after_summary.get("quality_report") or {}
    before_score=_quality_health_score(baseline_report)
    after_score=_quality_health_score(after_report)
    delta=round(after_score["score"]-before_score["score"],1)
    if delta >= 5:
        status="improved"; recommendation="保留本次修复；继续观察下一轮。"
    elif delta <= -5:
        status="regressed"; recommendation="修复后质量下降，建议回滚或换另一种 repair action。"
    else:
        status="neutral"; recommendation="效果不明显；如果连续两轮无改善，再考虑回滚或换策略。"
    return {"status":status,"delta":delta,"before":before_score,"after":after_score,"baseline_run_id":baseline.get("run_id"),"after_run_id":after_row.id,"after_started_at":after_row.started_at.isoformat(),"recommendation":recommendation}

def apply_repair_action(db: Session, action: str, source: str | None = None, value: str | None = None, record: bool = True) -> dict:
    """Apply safe, reversible internal repairs suggested by diagnosis."""
    action=(action or "").strip()
    before={}
    changed=[]
    if action == "add_commercial_seeds":
        key="COLLECTOR_AUTO_SEEDS"; before[key]=setting(db,key)
        additions=[
            "invoice late fee calculator", "shopify tax compliance app", "woocommerce return policy template",
            "vendor compliance tracking software", "appointment reminder template", "hubspot data cleanup tool",
            "stripe fee calculator", "quickbooks invoice reminder automation",
        ]
        seeds=_setting_list(db,key)+additions
        _save_setting_list(db,key,seeds,","); changed.append(key)
    elif action == "prune_generic_seeds":
        key="COLLECTOR_AUTO_SEEDS"; before[key]=setting(db,key)
        generic={"best","free","online","tool","software","app","calculator","template","booking"}
        seeds=[]
        for s in _setting_list(db,key):
            terms=set(re.findall(r"[a-z0-9]+", s.lower()))
            if terms and terms.issubset(generic):
                continue
            if len(terms & generic) >= max(2, len(terms)-1):
                continue
            seeds.append(s)
        _save_setting_list(db,key,seeds,","); changed.append(key)
    elif action == "increase_import_limit":
        key="COLLECTOR_AUTO_IMPORT_LIMIT"; before[key]=setting(db,key)
        try: current=int(setting(db,key) or "12")
        except Exception: current=12
        row=db.get(models.Setting,key) or models.Setting(key=key, value="12", secret=False)
        row.value=str(min(48, max(current+6, int(current*1.5))))
        row.secret=False; db.merge(row); changed.append(key)
    elif action == "enable_rewrite_recovery":
        for key,val in [("FOUR_FIND_REWRITE_ON_SERP_REJECT","true"),("FOUR_FIND_REWRITE_LIMIT","8")]:
            before[key]=setting(db,key)
            row=db.get(models.Setting,key) or models.Setting(key=key, value=val, secret=False)
            row.value=val; row.secret=False; db.merge(row); changed.append(key)
    elif action == "lower_source_weight":
        if not source:
            return {"ok":False,"error":"source required"}
        key="COLLECTOR_SOURCE_WEIGHTS"; before[key]=setting(db,key)
        try: weights=json.loads(setting(db,key) or "{}")
        except Exception: weights={}
        entry=weights.get(source,{}) if isinstance(weights.get(source,{}),dict) else {}
        entry["weight"]=round(max(0.25, min(2.5, float(entry.get("weight",1.0))-0.25)), 3)
        entry["repair_note"]="manual_lower_source_weight"
        weights[source]=entry
        row=db.get(models.Setting,key) or models.Setting(key=key, value="{}", secret=False)
        row.value=json.dumps(weights, ensure_ascii=False, sort_keys=True); row.secret=False; db.merge(row); changed.append(key)
    elif action == "pause_source":
        if not source:
            return {"ok":False,"error":"source required"}
        return apply_repair_action(db, "lower_source_weight", source=source, value=value)
    else:
        return {"ok":False,"error":"unknown repair action", "allowed":["add_commercial_seeds","prune_generic_seeds","increase_import_limit","enable_rewrite_recovery","lower_source_weight","pause_source"]}
    db.commit()
    after={k:setting(db,k) for k in changed}
    baseline_row=_latest_daily_with_quality(db)
    baseline_summary=_parse_run_summary(baseline_row)
    baseline={"run_id": baseline_row.id, "started_at": baseline_row.started_at.isoformat(), "quality_report": baseline_summary.get("quality_report")} if baseline_row and baseline_summary.get("quality_report") else None
    result={"ok":True,"action":action,"source":source,"changed":changed,"before":before,"after":after,"rolled_back":False,"baseline":baseline}
    if record:
        audit=_record_repair_audit(db, result)
        result["repair_id"]=audit.id
    return result

def list_repair_audits(db: Session, limit: int = 20) -> list[dict]:
    rows=db.query(models.RunHistory).filter(models.RunHistory.kind=="repair").order_by(models.RunHistory.started_at.desc()).limit(limit).all()
    out=[]
    strategy=repair_strategy_stats(db)
    for r in rows:
        try: summary=json.loads(r.summary or "{}")
        except Exception: summary={"raw":r.summary}
        effect=evaluate_repair_effect(db,r)
        key=f"{summary.get('action','')}:{summary.get('source') or ''}"
        if key in strategy:
            effect["strategy"]=strategy[key]
        out.append({"id":r.id,"status":r.status,"started_at":r.started_at.isoformat() if r.started_at else None,"finished_at":r.finished_at.isoformat() if r.finished_at else None,"summary":summary,"effect":effect})
    return out

def rollback_repair_action(db: Session, repair_id: int) -> dict:
    row=db.get(models.RunHistory, repair_id)
    if not row or row.kind != "repair":
        return {"ok":False,"error":"repair audit not found"}
    try: summary=json.loads(row.summary or "{}")
    except Exception: return {"ok":False,"error":"invalid repair audit summary"}
    if summary.get("rolled_back"):
        return {"ok":False,"error":"repair already rolled back"}
    before=summary.get("before") or {}
    if not isinstance(before, dict) or not before:
        return {"ok":False,"error":"repair has no rollback snapshot"}
    restored={}
    for key,value in before.items():
        setting_row=db.get(models.Setting,key) or models.Setting(key=key, value="", secret=False)
        setting_row.value=str(value or "")
        setting_row.secret=False
        db.merge(setting_row)
        restored[key]=setting_row.value
    summary["rolled_back"]=True
    summary["rolled_back_at"]=datetime.utcnow().isoformat(timespec="seconds")
    row.summary=json.dumps(summary, ensure_ascii=False)
    row.status="rolled_back"
    row.finished_at=datetime.utcnow()
    db.merge(row)
    rollback_payload={"ok":True,"action":"rollback_repair","repair_id":repair_id,"restored":restored}
    db.add(models.RunHistory(kind="repair_rollback", status="ok", summary=json.dumps(rollback_payload, ensure_ascii=False), finished_at=datetime.utcnow()))
    db.commit()
    return rollback_payload

def start_repair_experiment(db: Session, action: str, source: str | None = None, value: str | None = None, force_run: bool = True) -> dict:
    """Start a controlled one-change experiment.

    The experiment itself is an audit wrapper around one safe repair action. A
    background daily run can then evaluate that repair via the existing repair
    effect mechanism.
    """
    # Refresh old experiments first so completed ones close before concurrency check.
    active=[]
    for exp in list_repair_experiments(db, limit=20):
        if exp.get("status") == "running" or (exp.get("effect") or {}).get("status") in {"pending", "no_baseline"}:
            active.append(exp)
    if active:
        return {"ok":False,"error":"active_experiment_exists","message":"已有实验等待评估；为避免变量污染，请等待完成或回滚后再启动新实验。","active_experiment":active[0]}
    repair=apply_repair_action(db, action, source=source, value=value, record=True)
    if not repair.get("ok"):
        return {"ok":False,"error":repair.get("error","repair failed"),"repair":repair}
    payload={"ok":True,"kind":"repair_experiment","action":action,"source":source,"value":value,"repair_id":repair.get("repair_id"),"force_run":bool(force_run),"status":"repair_applied_run_pending" if force_run else "repair_applied"}
    exp=models.RunHistory(kind="repair_experiment", status="running" if force_run else "ok", summary=json.dumps(payload, ensure_ascii=False), finished_at=None if force_run else datetime.utcnow())
    db.add(exp); db.commit(); db.refresh(exp)
    payload["experiment_id"]=exp.id
    exp.summary=json.dumps(payload, ensure_ascii=False)
    db.merge(exp); db.commit()
    return {"ok":True,"experiment_id":exp.id,"repair":repair,"force_run":bool(force_run)}

def list_repair_experiments(db: Session, limit: int = 20) -> list[dict]:
    rows=db.query(models.RunHistory).filter(models.RunHistory.kind=="repair_experiment").order_by(models.RunHistory.started_at.desc()).limit(limit).all()
    out=[]
    for row in rows:
        summary=_parse_run_summary(row)
        repair_id=summary.get("repair_id")
        repair_row=db.get(models.RunHistory, repair_id) if repair_id else None
        effect=evaluate_repair_effect(db, repair_row) if repair_row else {"status":"no_repair"}
        guard={"status":"pending","label":"等待评估","recommendation":effect.get("note") or "等待实验后的 daily run 完成。","rollback_recommended":False}
        if row.status == "abandoned" or summary.get("status") == "abandoned":
            guard={"status":"abandoned","label":"已放弃","recommendation":"实验已手动放弃。","rollback_recommended":False}
            effect={**effect,"status":"abandoned","guard":guard}
            out.append({"id":row.id,"status":"abandoned","started_at":row.started_at.isoformat() if row.started_at else None,"finished_at":row.finished_at.isoformat() if row.finished_at else None,"summary":summary,"effect":effect})
            continue
        if effect.get("status") == "improved":
            guard={"status":"keep","label":"建议保留","recommendation":"实验改善了漏斗，保留本次 repair。","rollback_recommended":False}
        elif effect.get("status") == "regressed":
            guard={"status":"rollback_recommended","label":"建议回滚","recommendation":"实验后质量下降，建议点击回滚对应 repair。","rollback_recommended":True}
        elif effect.get("status") == "neutral":
            guard={"status":"observe","label":"继续观察","recommendation":"效果不明显；可再观察一轮或手动回滚。","rollback_recommended":False}
        elif effect.get("status") == "rolled_back":
            guard={"status":"rolled_back","label":"已回滚","recommendation":"实验关联 repair 已回滚。","rollback_recommended":False}
        effect["guard"]=guard
        status=row.status
        if row.status=="running" and effect.get("status") not in {"pending","no_baseline"}:
            status="ok"
            summary["status"]=guard["status"]
            summary["closed_at"]=datetime.utcnow().isoformat(timespec="seconds")
            summary["guard"]=guard
            row.status="ok"; row.finished_at=datetime.utcnow(); row.summary=json.dumps(summary, ensure_ascii=False); db.merge(row); db.commit()
        out.append({"id":row.id,"status":status,"started_at":row.started_at.isoformat() if row.started_at else None,"finished_at":row.finished_at.isoformat() if row.finished_at else None,"summary":summary,"effect":effect})
    return out

def abandon_repair_experiment(db: Session, experiment_id: int, rollback: bool = False) -> dict:
    row=db.get(models.RunHistory, experiment_id)
    if not row or row.kind != "repair_experiment":
        return {"ok":False,"error":"experiment not found"}
    summary=_parse_run_summary(row)
    if row.status == "abandoned" or summary.get("status") == "abandoned":
        return {"ok":False,"error":"experiment already abandoned"}
    repair_id=summary.get("repair_id")
    rollback_result=None
    if rollback and repair_id:
        rollback_result=rollback_repair_action(db, int(repair_id))
        if not rollback_result.get("ok"):
            return {"ok":False,"error":"rollback failed","rollback":rollback_result}
    summary["status"]="abandoned"
    summary["abandoned_at"]=datetime.utcnow().isoformat(timespec="seconds")
    summary["rollback_requested"]=bool(rollback)
    summary["rollback_result"]=rollback_result
    row.status="abandoned"
    row.finished_at=datetime.utcnow()
    row.summary=json.dumps(summary, ensure_ascii=False)
    db.merge(row)
    audit={"ok":True,"action":"abandon_repair_experiment","experiment_id":experiment_id,"repair_id":repair_id,"rollback":bool(rollback),"rollback_result":rollback_result}
    db.add(models.RunHistory(kind="repair_experiment_abandon", status="ok", summary=json.dumps(audit, ensure_ascii=False), finished_at=datetime.utcnow()))
    db.commit()
    return audit

def daily_run(db: Session, limit=12, roots=None, use_four_find: bool | None = None, seeds: list[str] | None = None) -> models.RunHistory:
    # recover stale runs from previous crashes/restarts so dashboard does not stay "running" forever
    stale = db.query(models.RunHistory).filter(models.RunHistory.status == "running", models.RunHistory.kind == "daily").all()
    for old in stale:
        old.status = "failed"
        old.summary = "stale running run recovered before new run"
        old.finished_at = datetime.utcnow()
    db.commit()
    run=models.RunHistory(kind="daily", status="running"); db.add(run); db.commit(); db.refresh(run)
    try:
        if use_four_find is None:
            use_four_find = (setting(db, "FOUR_FIND_AUTO_ENABLED") or "false").lower() in {"1", "true", "yes", "on"}
        collector_summary = None
        if (setting(db, "COLLECTOR_AUTO_ENABLED") or "false").lower() in {"1", "true", "yes", "on"}:
            try:
                from . import collectors as collector_service
                try:
                    collector_limit = int(setting(db, "COLLECTOR_AUTO_LIMIT") or "24")
                except Exception:
                    collector_limit = 24
                try:
                    collector_import_limit = int(setting(db, "COLLECTOR_AUTO_IMPORT_LIMIT") or "12")
                except Exception:
                    collector_import_limit = 12
                run.summary=json.dumps({"phase":"collectors", "collector_limit": collector_limit, "collector_import_limit": collector_import_limit}, ensure_ascii=False)
                db.commit()
                collector_summary = collector_service.run_collector_autopilot(db, limit=collector_limit, import_limit=collector_import_limit)
                print(f"[daily_run] collector done, selecting keywords", flush=True)
            except Exception as e:
                collector_summary = {"enabled": True, "error": str(e)[:240]}
        try:
            recheck_limit = int(setting(db, "AUTO_RECHECK_LIMIT") or "4") if (setting(db, "AUTO_RECHECK_ENABLED") or "true").lower() in {"1","true","yes","on"} else 0
        except Exception:
            recheck_limit = 4
        old_kws = select_old_keywords_for_recheck(db, limit=min(recheck_limit, max(0, limit)))
        print(f"[daily_run] old_kws={len(old_kws)}", flush=True)
        collector_kws = select_collector_keywords(db, limit=max(0, min(limit - len(old_kws), int((limit or 1) * 0.5))))
        print(f"[daily_run] collector_kws={len(collector_kws)}", flush=True)
        new_limit = max(0, limit - len(old_kws) - len(collector_kws))
        if use_four_find:
            kws = old_kws + collector_kws + discover_keywords_four_find(db, limit=new_limit, seeds=seeds)
            print(f"[daily_run] four_find kws={len(kws)}", flush=True)
            if len(kws) < limit:
                existing = {kw.query for kw in kws}
                for kw in discover_keywords(db, limit=limit, roots=roots):
                    if kw.query not in existing:
                        kws.append(kw)
                        existing.add(kw.query)
                    if len(kws) >= limit:
                        break
        else:
            kws=old_kws + collector_kws + discover_keywords(db, limit=new_limit, roots=roots)
        cards=[]
        skipped=[]
        processed=[]
        serp_gate_reasons={}
        kws = [kw for kw in kws if kw.status not in {"rejected", "reject", "block", "duplicate", "serp_reject", "rewrite_exhausted"}]
        total_kws = len(kws[:limit])
        for idx, kw in enumerate(kws[:limit], 1):
            run.summary=json.dumps({"phase":"running", "current": idx, "total": total_kws, "keyword": kw.query, "cards": len(cards)}, ensure_ascii=False)
            db.commit()
            noise = keyword_noise_reason(kw.query, kw.source)
            if noise:
                kw.status = "rejected"
                kw.intent = f"noise:{noise}"[:80]
                kw.score = 0.0
                db.commit()
                source_family = kw.source.split(":",1)[0] if kw.source else "unknown"
                source_detail = kw.source.split(":",1)[1] if ":" in (kw.source or "") else (kw.source or "unknown")
                processed.append({"keyword": kw.query, "source": kw.source, "source_family": source_family, "source_detail": source_detail, "status":"keyword_reject", "reason": noise})
                continue
            serp, strategy_meta = run_serp_with_strategy(db, kw)
            admissible, gate = serp_admissibility(serp)
            source_family = kw.source.split(":",1)[0] if ":" in kw.source else kw.source
            source_detail = kw.source.split(":",1)[1] if ":" in kw.source else kw.source
            if not admissible:
                mark_four_find_serp_reject(db, kw, gate)
                skipped.append({"keyword": kw.query, "serp_strategy": strategy_meta, **gate})
                reason = gate.get("reason") or "unknown"
                serp_gate_reasons[reason]=serp_gate_reasons.get(reason,0)+1
                processed.append({"keyword": kw.query, "source": kw.source, "source_family": source_family, "source_detail": source_detail, "status":"serp_reject", **gate})
                continue
            card=make_card(db, kw)
            if card.keyword_id != kw.id:
                processed.append({"keyword": kw.query, "source": kw.source, "source_family": source_family, "source_detail": source_detail, "status":"duplicate", "duplicate_card_id": card.id})
                continue
            cards.append(card)
            processed.append({"keyword": kw.query, "source": kw.source, "source_family": source_family, "source_detail": source_detail, "status":"card", "verdict": card.verdict, "score": card.score})
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
        collector_results = (collector_summary or {}).get("results") or []
        collector_by_source = []
        for r in collector_results:
            if isinstance(r, dict):
                collector_by_source.append({
                    "source": r.get("source") or "unknown",
                    "saved": r.get("saved", 0),
                    "seen": r.get("candidates_seen", r.get("urls_seen", 0)),
                    "new_urls": r.get("new_urls"),
                    "old_urls": r.get("old_urls"),
                    "errors": len(r.get("errors") or []),
                })
        clean = (collector_summary or {}).get("clean") or {}
        imported = (collector_summary or {}).get("import") or {}
        collector_self_repair_report = None
        if collector_summary and collector_summary.get("enabled", True):
            try:
                from . import collectors as collector_service
                collector_self_repair_report = collector_service.collector_autopilot_self_repair_report(db)
            except Exception as e:
                collector_self_repair_report = {"ok": False, "error": str(e)[:180]}
        card_by_source={}
        for p in processed:
            key=p.get("source") or "unknown"
            row=card_by_source.setdefault(key,{"processed":0,"cards":0,"action":0,"watch":0,"reject":0,"serp_reject":0})
            row["processed"] += 1
            if p.get("status") == "serp_reject": row["serp_reject"] += 1
            if p.get("status") == "card":
                row["cards"] += 1
                verdict=(p.get("verdict") or "").lower()
                if verdict in row: row[verdict] += 1
        quality_report={
            "collector": {
                "enabled": bool(collector_summary and collector_summary.get("enabled", True)),
                "budget_plan": (collector_summary or {}).get("budget_plan"),
                "by_source": collector_by_source,
                "errors": (collector_summary or {}).get("errors") or [],
                "pool": (collector_summary or {}).get("summary") or {},
                "clean": clean,
                "import": imported,
                "safe_repair": (collector_summary or {}).get("safe_repair"),
                "self_repair_report": collector_self_repair_report,
            },
            "funnel": {
                "collector_seen": sum(int(x.get("seen") or 0) for x in collector_by_source),
                "collector_saved": sum(int(x.get("saved") or 0) for x in collector_by_source),
                "clean_scanned": clean.get("scanned", 0),
                "clean_rejected": clean.get("rejected", 0),
                "import_selected": imported.get("selected", 0),
                "imported_keywords": imported.get("imported", 0),
                "keywords_processed": len(processed),
                "serp_rejected": len(skipped),
                "duplicates": sum(1 for p in processed if p.get("status") == "duplicate"),
                "cards": len(cards),
                "action": sum(1 for c in cards if c.verdict=="Action"),
                "watch": sum(1 for c in cards if c.verdict=="Watch"),
                "reject": sum(1 for c in cards if c.verdict=="Reject"),
            },
            "serp_gate_reasons": serp_gate_reasons,
            "card_by_source": card_by_source,
            "processed_examples": processed[:12],
        }
        diagnosis=diagnose_quality_report(quality_report, db=db)
        quality_report["diagnosis"] = diagnosis
        summary={
            "phase":"finished",
            "keywords":len(kws),
            "cards":len(cards),
            "action":sum(1 for c in cards if c.verdict=="Action"),
            "watch":sum(1 for c in cards if c.verdict=="Watch"),
            "reject":sum(1 for c in cards if c.verdict=="Reject"),
            "use_four_find": bool(use_four_find),
            "old_keywords_rechecked": len(old_kws),
            "new_keyword_budget": new_limit,
            "four_find_keywords": sum(1 for k in kws if k.source.startswith("four_find:")),
            "root_combo_keywords": sum(1 for k in kws if k.source == "root_combo"),
            "collector_keywords": sum(1 for k in kws if k.source.startswith("collector:")),
            "collector_summary": collector_summary,
            "quality_report": quality_report,
            "diagnosis": diagnosis,
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
    providers = {"available": available_serp_providers(db), "searxng_urls": len(searxng_urls(db)), "brave_keys": len(rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")), "tavily_keys": len(rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY")), "serpapi_keys": len(rotating_api_keys(db, "SERPAPI_API_KEYS", "")), "brave_configured": bool(rotating_api_keys(db, "BRAVE_API_KEYS", "BRAVE_API_KEY")), "tavily_configured": bool(rotating_api_keys(db, "TAVILY_API_KEYS", "TAVILY_API_KEY")), "serpapi_configured": bool(rotating_api_keys(db, "SERPAPI_API_KEYS", ""))}
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
    # Manual review is the final human verdict. Keep the visible card verdict in
    # sync with feedback so reviewed Reject/Watch cards disappear from Action
    # lists and exports immediately instead of remaining under their old model
    # verdict.
    if label in {"Adopted", "Action", "Watch", "Reject", "Block"}:
        card.verdict = label
    if label not in {"Adopted", "Action", "Watch", "Reject", "Block"}:
        db.commit(); db.refresh(card); return card
    kw = db.get(models.Keyword, card.keyword_id)
    roots = []
    if kw:
        try: roots = json.loads(kw.root_terms or "[]")
        except Exception: roots = []
        kw.status = label.lower()
        collector_feedback = None
        if kw.source.startswith("collector:"):
            try:
                from . import collectors as collector_service
                collector_feedback = collector_service.apply_collector_feedback(db, kw, label)
            except Exception as e:
                collector_feedback = {"applied": False, "error": str(e)[:180]}
            try:
                evidence = json.loads(card.evidence_json or "[]")
                if isinstance(evidence, list):
                    evidence.append({"type":"collector_feedback", "data": collector_feedback})
                    card.evidence_json = json.dumps(evidence, ensure_ascii=False)
            except Exception:
                pass
        # Four-Find closed loop: feedback on generated cards should change the
        # next discovery cycle, not just the card label.
        if kw.source.startswith("four_find:"):
            good = label in {"Adopted", "Action", "Watch"}
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
    delta = {"Adopted": 0.35, "Action": 0.2, "Watch": 0.05, "Reject": -0.15, "Block": -0.5}.get(label, 0)
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
    # The automatic loop's primary run is `daily`. Collector/repair rows are
    # child steps emitted during the same loop; using them as `last_run` makes
    # the dashboard look like the real auto run is missing or shifts the next
    # scheduled time. Fall back to any run only before the first daily exists.
    last = db.query(models.RunHistory).filter_by(kind="daily").order_by(models.RunHistory.started_at.desc()).first()
    if not last:
        last = db.query(models.RunHistory).order_by(models.RunHistory.started_at.desc()).first()
    enabled = (setting(db, "AUTO_RUN_ENABLED") or "false").lower() in {"1","true","yes","on"}
    try: interval = int(setting(db, "AUTO_RUN_INTERVAL_MINUTES") or "360")
    except Exception: interval = 360
    def iso_bj(dt):
        return (dt + timedelta(hours=8)).isoformat() + "+08:00" if dt else None
    next_run_at = iso_bj(last.finished_at + timedelta(minutes=interval)) if last and last.finished_at and enabled else None
    return {"enabled": enabled, "interval_minutes": interval, "timezone": "Asia/Shanghai", "next_run_at": next_run_at, "last_run": None if not last else {"id": last.id, "status": last.status, "kind": last.kind, "summary": json.loads(last.summary or "{}") if last.summary and last.summary.startswith("{") else last.summary, "started_at": iso_bj(last.started_at), "finished_at": iso_bj(last.finished_at)}}

def auto_due(db: Session) -> bool:
    st = auto_status(db)
    if not st["enabled"]: return False
    last = db.query(models.RunHistory).filter_by(kind="daily").order_by(models.RunHistory.started_at.desc()).first()
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
    latest_daily = db.query(models.RunHistory).filter_by(kind="daily", status="ok").order_by(models.RunHistory.started_at.desc()).first()
    audit_report=None; audit_label=None
    if latest_daily:
        try: daily_summary=json.loads(latest_daily.summary or "{}")
        except Exception: daily_summary={}
        sr=((daily_summary.get("quality_report") or {}).get("collector") or {}).get("self_repair_report") or {}
        if sr.get("ok") and sr.get("report"):
            audit_report=sr.get("report"); audit_label=f"Daily Run: #{latest_daily.id}"
        elif (daily_summary.get("collector_summary") or {}).get("safe_repair"):
            safe=(daily_summary.get("collector_summary") or {}).get("safe_repair") or {}
            audit_report=f"Safe repair applied: {safe.get('applied_count')}\nSafe repair blocked: {safe.get('blocked_count')}"; audit_label=f"Daily Run: #{latest_daily.id}"
    if not audit_report:
        try:
            from . import collectors as collector_service
            sr=collector_service.collector_autopilot_self_repair_report(db)
            if sr.get("ok") and sr.get("report"):
                audit_report=sr.get("report"); audit_label=f"Collector Run: #{sr.get('run_id')}"
        except Exception:
            audit_report=None
    if audit_report:
        lines += ["## Collector Autopilot / Safe Repair Audit", "", audit_label or "Latest Collector Run", "", "```text", audit_report, "```", ""]
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

def export_action_execution_markdown(db: Session, min_score: int | None = None) -> str:
    from pathlib import Path
    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    if min_score is None:
        try: min_score = int(setting(db, "MIN_ACTION_SCORE") or "74")
        except Exception: min_score = 74
    cards = (
        db.query(models.OpportunityCard)
        .filter(models.OpportunityCard.verdict == "Action")
        .filter(models.OpportunityCard.score >= min_score)
        .order_by(models.OpportunityCard.score.desc(), models.OpportunityCard.created_at.desc())
        .limit(50)
        .all()
    )
    lines = ["# Demand Hunter Action Execution List", "", f"Generated: {datetime.utcnow().isoformat()}Z", f"Min Action Score: {min_score}", f"Count: {len(cards)}", ""]
    for idx,c in enumerate(cards,1):
        kw = db.get(models.Keyword, c.keyword_id)
        try: evidence = json.loads(c.evidence_json or "[]")
        except Exception: evidence = []
        business = next((e for e in evidence if e.get("type") == "business"), {})
        web_evidence = [e for e in evidence if e.get("type") != "business"][:5]
        try: risks = json.loads(c.risks or "[]")
        except Exception: risks = []
        lines += [f"## {idx}. {c.title}", "", f"- Score: {c.score}", f"- Keyword: {kw.query if kw else '-'}", f"- Monetization: {business.get('business_type') or c.monetization_type or '-'}", f"- ICP: {business.get('icp') or '-'}", ""]
        first_sale = business.get("first_sale_test") or []
        lines += ["### First validation", ""]
        if first_sale:
            lines += [f"{i+1}. {x}" for i,x in enumerate(first_sale[:5])]
        else:
            lines += [business.get("commercial_mvp") or c.mvp_plan or "-"]
        lines += ["", "### MVP", "", business.get("commercial_mvp") or c.mvp_plan or "-", "", "### Revenue path", "", business.get("revenue_path") or c.monetization_type or "-"]
        if business.get("pricing"):
            lines += ["", f"Pricing: {business.get('pricing')}"]
        if business.get("gtm") or business.get("wedge"):
            lines += ["", "### GTM / Wedge", "", f"- GTM: {business.get('gtm') or '-'}", f"- Wedge: {business.get('wedge') or '-'}"]
        if risks:
            lines += ["", "### Risks", ""] + [f"- {r}" for r in risks[:6]]
        if web_evidence:
            lines += ["", "### Evidence", ""] + [f"- [{e.get('type','web')}] {e.get('title','')} {e.get('url','')}" for e in web_evidence]
        lines += [""]
    path = out_dir / "action_execution_list.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)

def export_card_markdown(db: Session, card_id: int) -> str:
    from pathlib import Path
    out_dir = ROOT / "output" / "cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    c = db.get(models.OpportunityCard, card_id)
    if not c:
        raise ValueError("card not found")
    kw = db.get(models.Keyword, c.keyword_id)
    try: evidence = json.loads(c.evidence_json or "[]")
    except Exception: evidence = []
    business = next((e for e in evidence if isinstance(e, dict) and e.get("type") == "business"), {})
    web_evidence = [e for e in evidence if isinstance(e, dict) and e.get("type") != "business"]
    try: risks = json.loads(c.risks or "[]")
    except Exception: risks = []
    lines = [
        f"# Opportunity Card: {c.title}", "",
        "## Summary", "",
        f"- Card ID: {c.id}",
        f"- Verdict: {c.verdict}",
        f"- Score: {c.score}",
        f"- Keyword: {kw.query if kw else '-'}",
        f"- Keyword Source: {kw.source if kw else '-'}",
        f"- Intent: {kw.intent if kw else '-'}",
        f"- Monetization Type: {business.get('business_type') or c.monetization_type or '-'}",
        f"- Created At: {c.created_at}", "",
        "## Scores", "",
        f"- Demand: {c.demand_score}",
        f"- SERP Gap: {c.serp_gap_score}",
        f"- Competitor Weakness: {c.competitor_weakness_score}",
        f"- MVP Feasibility: {c.mvp_score}",
        f"- Monetization: {c.monetization_score}", "",
    ]
    if business:
        lines += [
            "## Commercialization Brief", "",
            f"- Go/No-Go: {business.get('go_no_go','-')}",
            f"- Commercial Score: {business.get('commercial_score','-')}",
            f"- Keyword Type: {business.get('keyword_type','-')}",
            f"- SEO Fit: {business.get('seo_fit','-')}",
            "", "### ICP", "", business.get("icp") or "-",
            "", "### Pain / Pay Trigger", "", business.get("pay_trigger") or "-",
            "", "### Commercial MVP", "", business.get("commercial_mvp") or c.mvp_plan or "-",
            "", "### Revenue Path", "", business.get("revenue_path") or c.monetization_type or "-",
            "", "### Pricing", "", business.get("pricing") or "-",
            "", "### GTM", "", business.get("gtm") or "-",
            "", "### Wedge", "", business.get("wedge") or "-",
            "", "### Key Assumption", "", business.get("key_assumption") or "-",
            "", "### Verdict Reason", "", business.get("verdict_reason") or "-",
        ]
        if business.get("first_sale_test"):
            lines += ["", "### First Sale Test", ""] + [f"{i+1}. {x}" for i,x in enumerate(business.get("first_sale_test") or [])]
        if business.get("missing_evidence"):
            lines += ["", "### Missing Evidence", ""] + [f"- {x}" for x in (business.get("missing_evidence") or [])]
    lines += ["", "## MVP Plan", "", c.mvp_plan or "-"]
    if risks:
        lines += ["", "## Risks", ""] + [f"- {r}" for r in risks]
    if web_evidence:
        lines += ["", "## Evidence Links", ""]
        for e in web_evidence:
            lines.append(f"- [{e.get('type','web')}] {e.get('title','')} — {e.get('url','')}")
    lines += ["", "## Raw Evidence JSON", "", "```json", json.dumps(evidence, ensure_ascii=False, indent=2), "```", ""]
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", c.title.lower()).strip("-")[:80] or f"card-{c.id}"
    path = out_dir / f"card-{c.id}-{safe}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
