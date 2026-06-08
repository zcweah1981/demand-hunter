from __future__ import annotations
import gzip, io, json, re, time
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote
import requests
from sqlalchemy.orm import Session
from . import models, services

STOPWORDS={"best","top","free","online","app","apps","software","tool","tools","page","blog","pricing","login","signup","about","contact","privacy","terms","docs","help","features","category","tag","author","news","article","post","posts","product","products","en","www"}
TOOL_INTENT_TERMS={"calculator","generator","template","checker","converter","tracker","dashboard","analyzer","builder","creator","planner","estimator","form","spreadsheet","invoice","policy","report","monitor","automation","integration","api"}
TOOL_INTENT_PLURALS={"calculators":"calculator","generators":"generator","templates":"template","checkers":"checker","converters":"converter","trackers":"tracker","dashboards":"dashboard","analyzers":"analyzer","builders":"builder","planners":"planner","estimators":"estimator","forms":"form","spreadsheets":"spreadsheet","reports":"report","monitors":"monitor","automations":"automation","integrations":"integration","apis":"api"}
COMMERCIAL_TERMS={"pricing","price","cost","fee","invoice","tax","compliance","shopify","woocommerce","quickbooks","hubspot","salesforce","stripe","paypal","b2b","business","agency","client","contractor","clinic","rental"}
EARLY_SOURCE_BONUS={"sitemap":0.16,"advanced_search":0.12,"hn_algolia":0.10,"arxiv":0.08,"google_suggest":0.06,"duckduckgo":0.05}
NOISE_DOMAINS={"github.com","raw.githubusercontent.com","gist.github.com"}
NOISE_TITLE_PATTERNS=(
    r"\bpull request\b", r"\bissue\b", r"\bcommit\b", r"\bmerge pull request\b",
    r"\bfix\b.*\b(generator|bug|test|ci|build)\b", r"\battempt to\b",
    r"\blabels?\b", r"\bmilestone\b", r"\brelease notes?\b", r"\bchangelog\b",
    r"\bdocumentation\b", r"\bdocs?\b", r"\breadme\b",
)

def domain_of(url:str)->str:
    try: return urlparse(url).netloc.lower().removeprefix('www.')
    except Exception: return ''

def keyword_from_url(url:str)->str:
    path=unquote(urlparse(url).path or '')
    parts=[p for p in re.split(r"[/._\-+]+", path.lower()) if p]
    parts=[p for p in parts if not re.fullmatch(r"\d{2,4}|html?|php|aspx|index", p)]
    parts=[p for p in parts if p not in STOPWORDS]
    if not parts: return ''
    # Prefer last meaningful slug, but keep 2-6 terms.
    tail=parts[-6:]
    return ' '.join(tail).strip()

def normalize_keyword(text:str)->str:
    s=re.sub(r"[^a-zA-Z0-9\s\-_/]+", " ", text or "").lower()
    s=re.sub(r"[_/\-]+", " ", s)
    s=re.sub(r"\s+", " ", s).strip()
    terms=[TOOL_INTENT_PLURALS.get(t,t) for t in s.split() if t not in STOPWORDS]
    if len(terms)<2: return ''
    return ' '.join(terms[:8])


NOISE_TERMS={"best","top","free","online","2024","2025","2026","review","reviews","download","apk","crack","coupon","promo","cheap"}
CANONICAL_DROP_TERMS=NOISE_TERMS|{"tool","tools","app","apps","software","website","web","service","services"}

def canonical_keyword(keyword:str)->str:
    kw=normalize_keyword(keyword)
    if not kw: return ''
    terms=[t for t in kw.split() if t not in CANONICAL_DROP_TERMS]
    # Preserve order, drop duplicates.
    out=[]
    for t in terms:
        if t not in out: out.append(t)
    if len(out)<2: return kw
    return ' '.join(out[:8])

def candidate_noise_reason(keyword:str, evidence:dict|None=None)->str:
    evidence=evidence or {}
    kw=normalize_keyword(keyword)
    if not kw: return 'empty_or_too_short'
    terms=kw.split()
    url=str(evidence.get('url') or evidence.get('source_url') or '')
    title=str(evidence.get('title') or '')
    query=str(evidence.get('query') or '')
    d=domain_of(url)
    text=f"{kw} {title} {url} {query}".lower()
    if d in NOISE_DOMAINS:
        return 'developer_platform_noise'
    if any(re.search(p, text) for p in NOISE_TITLE_PATTERNS):
        return 'developer_or_documentation_noise'
    if re.search(r"\b(after|before):\d{4}-\d{2}-\d{2}\b", text) and not any(t in kw for t in TOOL_INTENT_TERMS|COMMERCIAL_TERMS):
        return 'search_operator_noise'
    if re.search(r"\b(after|before)\b", kw):
        return 'search_operator_noise'
    if len(terms)>9: return 'too_long'
    if len(terms)<2: return 'too_short'
    if len(set(terms)) < max(2, len(terms)-1): return 'repeated_terms'
    if any(t in {"crack","apk","coupon","promo"} for t in terms): return 'low_commercial_quality'
    if all(t in NOISE_TERMS for t in terms): return 'generic_noise'
    return ''

def candidate_quality_reject_reason(keyword:str, source:str, evidence:dict|None=None)->str:
    """Source-specific quality gate before a candidate enters the importable pool.

    Suggest/autocomplete may be broad, but SERP-derived collectors are noisy:
    titles from repos, docs, news, HN/arXiv, and generic pages can look like
    keywords. For those sources require both a concrete tool/task word and a
    commercial/vertical modifier.
    """
    kw=normalize_keyword(keyword)
    if not kw:
        return 'empty_or_too_short'
    terms=set(kw.split())
    has_tool=bool(terms & TOOL_INTENT_TERMS)
    has_commercial=bool(terms & COMMERCIAL_TERMS)
    tool_count=len(terms & (TOOL_INTENT_TERMS - {"invoice","policy","report","api"}))
    commercial_count=len(terms & COMMERCIAL_TERMS)
    ordered=kw.split()
    if len(ordered) >= 3 and ordered[0] in {"calculator","template","generator","tool","software","app"} and tool_count >= 2:
        return 'tool_category_slug'
    if tool_count >= 2 and commercial_count <= 1 and source in {'advanced_search','hn_algolia','arxiv'}:
        return 'tool_word_stack'
    if source in {'advanced_search','hn_algolia','arxiv'}:
        if not has_tool:
            return 'missing_tool_intent'
        if not has_commercial:
            return 'missing_commercial_modifier'
        root=(evidence or {}).get('root') or (evidence or {}).get('seed') or ''
        root_terms=set(normalize_keyword(root).split()) if root else set()
        if root_terms and not (terms & root_terms):
            return 'root_mismatch'
    # Generic task words alone create endless duplicate pseudo-opportunities.
    generic_tools={'calculator','template','generator','tool','software','app'}
    if terms and terms.issubset(generic_tools | NOISE_TERMS):
        return 'generic_tool_only'
    return ''

def clean_candidate_pool(db:Session, limit:int=1000)->dict:
    """Canonicalize, suppress near-duplicates, and reject obvious noise.

    We do not delete evidence. Lower quality variants are marked rejected with a
    duplicate_of pointer in evidence_json; the highest-score freshest candidate
    per canonical keyword remains new/importable.
    """
    rows=db.query(models.CandidateKeyword).filter(models.CandidateKeyword.status=='new').order_by(models.CandidateKeyword.score.desc(), models.CandidateKeyword.created_at.desc()).limit(limit).all()
    groups={}; rejected=0; updated=0; kept=0
    for r in rows:
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        reason=candidate_noise_reason(r.keyword, ev)
        canon=canonical_keyword(r.keyword)
        ev['canonical_keyword']=canon
        if reason:
            ev['reject_reason']=reason
            r.status='rejected'
            r.evidence_json=json.dumps(ev, ensure_ascii=False)
            db.merge(r); rejected+=1; continue
        groups.setdefault(canon, []).append((r,ev))
    for canon, items in groups.items():
        items.sort(key=lambda x: (x[0].score, x[0].created_at), reverse=True)
        keeper, keeper_ev=items[0]
        keeper_ev['canonical_keyword']=canon
        keeper_ev['cluster_size']=len(items)
        keeper.evidence_json=json.dumps(keeper_ev, ensure_ascii=False)
        db.merge(keeper); kept+=1; updated+=1
        for dup, ev in items[1:]:
            ev['canonical_keyword']=canon
            ev['duplicate_of']=keeper.id
            ev['reject_reason']='duplicate_variant'
            dup.status='rejected'
            dup.evidence_json=json.dumps(ev, ensure_ascii=False)
            db.merge(dup); rejected+=1; updated+=1
    db.commit()
    return {'ok':True,'scanned':len(rows),'kept_clusters':kept,'rejected':rejected,'updated':updated}

def score_candidate(keyword:str, source:str, evidence:dict|None=None, base:float=0.0)->float:
    """Free-first candidate scoring from article-method signals.

    Score is intentionally conservative: it ranks candidates for validation, it
    never marks a candidate as an opportunity directly.
    """
    evidence=evidence or {}
    kw=normalize_keyword(keyword)
    if not kw: return 0.0
    terms=kw.split()
    score=max(base, 0.35)
    score += EARLY_SOURCE_BONUS.get(source, 0.04)
    if any(t in TOOL_INTENT_TERMS for t in terms): score += 0.16
    if any(t in COMMERCIAL_TERMS for t in terms): score += 0.14
    if 2 <= len(terms) <= 6: score += 0.06
    if len(terms) > 8: score -= 0.12
    if evidence.get('is_new_url'): score += 0.18
    if evidence.get('variant') in {'allintitle_after','site_after'}: score += 0.10
    if evidence.get('provider') in {'serpapi','zenserp','scaleserp'}: score += 0.04
    if re.search(r"\b(best|top|free|202[0-9])\b", kw): score -= 0.08
    if len(set(terms)) < len(terms): score -= 0.06
    return round(max(0.0, min(1.0, score)), 3)

def _collector_source_weights(db:Session)->dict:
    try:
        data=json.loads(services.setting(db,'COLLECTOR_SOURCE_WEIGHTS') or '{}')
        return data if isinstance(data,dict) else {}
    except Exception:
        return {}

def _save_collector_source_weights(db:Session, weights:dict)->None:
    row=db.get(models.Setting,'COLLECTOR_SOURCE_WEIGHTS') or models.Setting(key='COLLECTOR_SOURCE_WEIGHTS', value='{}', secret=False)
    row.value=json.dumps(weights, ensure_ascii=False, sort_keys=True)
    row.secret=False
    db.merge(row)

def collector_source_multiplier(db:Session, source:str)->float:
    weights=_collector_source_weights(db)
    raw=weights.get(source,{}).get('weight', 1.0) if isinstance(weights.get(source,{}),dict) else 1.0
    try: return max(0.25, min(2.5, float(raw)))
    except Exception: return 1.0

def _collector_family_weight(db:Session, family:str)->float:
    aliases={
        'suggest':['google_suggest','duckduckgo'],
        'sitemap':['sitemap'],
        'advanced_search':['advanced_search'],
        'source_radar':['hn_algolia','arxiv'],
    }.get(family,[family])
    vals=[collector_source_multiplier(db,a) for a in aliases]
    return round(sum(vals)/max(1,len(vals)), 3)

def collector_budget_plan(db:Session, limit:int=24)->dict:
    """Allocate per-run collector budget from feedback-learned source weights."""
    try: min_weight=float(services.setting(db,'COLLECTOR_AUTO_MIN_WEIGHT') or '0.35')
    except Exception: min_weight=0.35
    families=[
        {'key':'suggest','setting':'COLLECTOR_AUTO_SUGGEST_ENABLED','unit':'seeds'},
        {'key':'advanced_search','setting':'COLLECTOR_AUTO_ADVANCED_ENABLED','unit':'roots'},
        {'key':'source_radar','setting':'COLLECTOR_AUTO_SOURCE_RADAR_ENABLED','unit':'seeds'},
        {'key':'sitemap','setting':'COLLECTOR_AUTO_SITEMAP_ENABLED','unit':'domains'},
    ]
    active=[]; paused=[]
    for f in families:
        enabled=(services.setting(db,f['setting']) or 'true').lower() in {'1','true','yes','on'}
        weight=_collector_family_weight(db, f['key'])
        row={**f,'enabled':enabled,'weight':weight}
        if enabled and weight >= min_weight:
            active.append(row)
        else:
            row['pause_reason']='disabled' if not enabled else f'weight<{min_weight}'
            paused.append(row)
    total_weight=sum(x['weight'] for x in active) or 1.0
    for row in active:
        share=row['weight']/total_weight
        row['share']=round(share,3)
        row['item_limit']=max(1, min(20, round(share * max(4, limit))))
        # Per-query limits are intentionally smaller for SERP-heavy collectors.
        if row['key']=='advanced_search':
            row['limit_per_query']=max(3, min(10, round(4 + row['weight']*2)))
        elif row['key']=='source_radar':
            row['limit_per_seed']=max(4, min(12, round(5 + row['weight']*2)))
        elif row['key']=='sitemap':
            row['max_urls_per_domain']=max(20, min(160, round(limit * 4 * row['weight'])))
    return {'limit':limit,'min_weight':min_weight,'active':active,'paused':paused,'weights':_collector_source_weights(db)}

def mark_sitemap_seen(db:Session, url:str, keyword:str)->bool:
    """Return True when URL is first seen, otherwise update last_seen metadata."""
    row=db.query(models.SitemapSeenUrl).filter_by(url=url).first()
    now=datetime.utcnow()
    if row:
        row.last_seen_at=now
        row.seen_count=(row.seen_count or 0)+1
        row.last_keyword=keyword[:260]
        db.merge(row)
        return False
    db.add(models.SitemapSeenUrl(url=url, domain=domain_of(url), first_seen_at=now, last_seen_at=now, seen_count=1, last_keyword=keyword[:260]))
    return True

def upsert_candidate(db:Session, keyword:str, source:str, source_url:str='', source_domain:str='', method:str='', evidence:dict|None=None, score:float=0.0):
    kw=normalize_keyword(keyword)
    if not kw: return None
    evidence=evidence or {}
    evidence.setdefault('url', source_url or '')
    evidence.setdefault('source_domain', source_domain or domain_of(source_url or ''))
    reason=candidate_noise_reason(kw, evidence) or candidate_quality_reject_reason(kw, source, evidence)
    if reason:
        # Store rejected evidence for observability, but never let obvious source
        # noise enter the importable candidate pool.
        q=db.query(models.CandidateKeyword).filter_by(keyword=kw, source=source, source_url=source_url or '').first()
        ev={**evidence, 'reject_reason': reason, 'canonical_keyword': canonical_keyword(kw)}
        if q:
            q.status='rejected'; q.evidence_json=json.dumps({**(json.loads(q.evidence_json or '{}') if q.evidence_json else {}), **ev}, ensure_ascii=False); db.merge(q); return None
        row=models.CandidateKeyword(keyword=kw, source=source, source_url=source_url or '', source_domain=source_domain or '', method=method, evidence_json=json.dumps(ev, ensure_ascii=False), score=0.0, status='rejected')
        db.add(row); return None
    computed_score=round(max(0.0, min(1.0, score_candidate(kw, source, evidence, score) * collector_source_multiplier(db, source))), 3)
    q=db.query(models.CandidateKeyword).filter_by(keyword=kw, source=source, source_url=source_url or '').first()
    if q:
        if q.status != 'new':
            return None
        q.score=max(q.score, computed_score)
        q.evidence_json=json.dumps({**(json.loads(q.evidence_json or '{}') if q.evidence_json else {}), **(evidence or {})}, ensure_ascii=False)
        db.merge(q); return q
    row=models.CandidateKeyword(keyword=kw, source=source, source_url=source_url or '', source_domain=source_domain or '', method=method, evidence_json=json.dumps(evidence or {}, ensure_ascii=False), score=computed_score, status='new')
    db.add(row); return row

def _fetch(url:str, timeout=15)->bytes:
    r=requests.get(url, headers={'User-Agent':'DemandHunterBot/1.0 (+sitemap watcher)'}, timeout=timeout)
    r.raise_for_status()
    data=r.content
    if url.endswith('.gz'):
        data=gzip.GzipFile(fileobj=io.BytesIO(data)).read()
    return data

def discover_sitemaps(domain_or_url:str)->list[str]:
    base=domain_or_url.strip()
    if not base.startswith('http'):
        base='https://'+base
    parsed=urlparse(base)
    root=f'{parsed.scheme}://{parsed.netloc}'
    out=[]
    try:
        txt=_fetch(urljoin(root,'/robots.txt')).decode('utf-8','ignore')
        for m in re.finditer(r"(?im)^\s*Sitemap:\s*(\S+)", txt):
            out.append(m.group(1).strip())
    except Exception:
        pass
    out.append(urljoin(root,'/sitemap.xml'))
    seen=[]
    for u in out:
        if u not in seen: seen.append(u)
    return seen[:20]

def parse_sitemap_urls(sitemap_url:str, max_urls=200)->tuple[list[str], list[str]]:
    data=_fetch(sitemap_url).decode('utf-8','ignore')
    locs=re.findall(r"<loc>\s*([^<]+)\s*</loc>", data, flags=re.I)
    sitemap_locs=[u for u in locs if 'sitemap' in u.lower() and not re.search(r"\.(html?|php)$", u, re.I)]
    page_locs=[u for u in locs if u not in sitemap_locs]
    return page_locs[:max_urls], sitemap_locs[:20]

def run_sitemap_watcher(db:Session, domains:list[str], max_urls_per_domain=80, only_new:bool=True)->dict:
    total=0; imported=0; new_urls=0; old_urls=0; errors=[]
    for d in domains:
        try:
            queue=discover_sitemaps(d); seen=set(); pages=[]
            while queue and len(pages)<max_urls_per_domain:
                sm=queue.pop(0)
                if sm in seen: continue
                seen.add(sm)
                try:
                    page_locs, child_sitemaps=parse_sitemap_urls(sm, max_urls=max_urls_per_domain-len(pages))
                    pages.extend(page_locs)
                    queue.extend([x for x in child_sitemaps if x not in seen])
                except Exception as e:
                    errors.append({'domain':d,'sitemap':sm,'error':str(e)[:180]})
            for url in pages[:max_urls_per_domain]:
                kw=keyword_from_url(url)
                if not kw: continue
                total+=1
                is_new=mark_sitemap_seen(db, url, kw)
                if is_new: new_urls+=1
                else: old_urls+=1
                if only_new and not is_new:
                    continue
                evidence={'url':url,'is_new_url':is_new,'first_seen_at':datetime.utcnow().isoformat(timespec='seconds') if is_new else None}
                row=upsert_candidate(db, kw, 'sitemap', url, domain_of(url), '站找词', evidence, 0.50)
                if row: imported+=1
        except Exception as e:
            errors.append({'domain':d,'error':str(e)[:180]})
    db.commit()
    return {'ok':True,'source':'sitemap','domains':len(domains),'urls_seen':total,'new_urls':new_urls,'old_urls':old_urls,'saved':imported,'only_new':only_new,'errors':errors[:20]}

def suggest_queries(seed:str, timeout:float=5)->list[dict]:
    out=[]
    seed=seed.strip()
    if not seed: return out
    endpoints=[
        ('duckduckgo', 'https://duckduckgo.com/ac/', {'q':seed,'type':'list'}),
        ('google_suggest', 'https://suggestqueries.google.com/complete/search', {'client':'firefox','q':seed,'hl':'en'}),
    ]
    for source,url,params in endpoints:
        try:
            r=requests.get(url, params=params, headers={'User-Agent':'Mozilla/5.0'}, timeout=timeout)
            r.raise_for_status(); data=r.json()
            if source=='duckduckgo':
                for x in data: out.append({'keyword':x.get('phrase') or x.get('word') or '', 'source':source})
            else:
                for x in (data[1] if isinstance(data,list) and len(data)>1 else []): out.append({'keyword':x,'source':source})
        except Exception:
            continue
    seen=set(); clean=[]
    for x in out:
        kw=normalize_keyword(x.get('keyword',''))
        if kw and kw not in seen:
            seen.add(kw); clean.append({'keyword':kw,'source':x['source']})
    return clean[:50]

def run_suggest_collector(db:Session, seeds:list[str], max_seconds:int|None=None)->dict:
    try:
        max_seconds=int(max_seconds if max_seconds is not None else (services.setting(db,'COLLECTOR_SUGGEST_MAX_SECONDS') or '20'))
    except Exception:
        max_seconds=20
    started=time.monotonic()
    saved=0; seen=0; errors=[]
    for seed in seeds:
        if time.monotonic() - started > max_seconds:
            errors.append({'seed':seed,'error':f'time_budget_exceeded>{max_seconds}s'})
            break
        for item in suggest_queries(seed, timeout=4):
            seen+=1
            row=upsert_candidate(db, item['keyword'], item['source'], '', '', '词找词', {'seed':seed,'provider':item['source']}, 0.55)
            if row: saved+=1
    db.commit()
    return {'ok':True,'source':'suggest','seeds':len(seeds),'candidates_seen':seen,'saved':saved,'errors':errors[:20]}

def import_candidates_to_keywords(db:Session, limit:int=30)->dict:
    # Clean first so the import step receives one representative per canonical keyword.
    clean=clean_candidate_pool(db, limit=max(200, limit*5))
    rows=db.query(models.CandidateKeyword).filter_by(status='new').order_by(models.CandidateKeyword.score.desc(), models.CandidateKeyword.created_at.desc()).limit(limit).all()
    imported=0; skipped_existing=0
    for c in rows:
        try: ev=json.loads(c.evidence_json or '{}')
        except Exception: ev={}
        query=ev.get('canonical_keyword') or canonical_keyword(c.keyword) or c.keyword
        existing=db.query(models.Keyword).filter_by(query=query).first()
        if not existing:
            db.add(models.Keyword(query=query, source=f'collector:{c.source}', root_terms='[]', score=c.score, status='new'))
            imported+=1
        else:
            skipped_existing+=1
        c.status='imported'
        ev['imported_query']=query
        c.evidence_json=json.dumps(ev, ensure_ascii=False)
        db.merge(c)
    db.commit()
    return {'ok':True,'selected':len(rows),'imported':imported,'skipped_existing':skipped_existing,'clean':clean}

def collector_pool_summary(db:Session)->dict:
    rows=db.query(models.CandidateKeyword.status, models.CandidateKeyword.source).all()
    by_status={}; by_source={}
    for status, source in rows:
        by_status[status or 'unknown']=by_status.get(status or 'unknown',0)+1
        by_source[source or 'unknown']=by_source.get(source or 'unknown',0)+1
    top_new=db.query(models.CandidateKeyword).filter_by(status='new').order_by(models.CandidateKeyword.score.desc(), models.CandidateKeyword.created_at.desc()).limit(8).all()
    top=[]
    for r in top_new:
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        top.append({'id':r.id,'keyword':r.keyword,'canonical_keyword':ev.get('canonical_keyword') or canonical_keyword(r.keyword),'source':r.source,'method':r.method,'score':r.score,'source_url':r.source_url})
    return {'total':sum(by_status.values()),'by_status':by_status,'by_source':by_source,'source_weights':_collector_source_weights(db),'budget_plan':collector_budget_plan(db),'top_new':top}

def _match_imported_candidates_for_keyword(db:Session, keyword_query:str, source:str)->list[tuple[models.CandidateKeyword,dict]]:
    source=source.removeprefix('collector:')
    rows=db.query(models.CandidateKeyword).filter_by(source=source).order_by(models.CandidateKeyword.created_at.desc()).limit(250).all()
    out=[]
    target=canonical_keyword(keyword_query) or normalize_keyword(keyword_query)
    for r in rows:
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        aliases={normalize_keyword(r.keyword), canonical_keyword(r.keyword), normalize_keyword(ev.get('imported_query','')), canonical_keyword(ev.get('imported_query','')), normalize_keyword(ev.get('canonical_keyword',''))}
        if target and target in aliases:
            out.append((r,ev))
    return out

def apply_collector_feedback(db:Session, keyword, label:str)->dict:
    """Closed-loop learning for collector-origin opportunity feedback.

    Action/Watch promotes source weight and seeds/domains; Reject/Block demotes
    them and suppresses matching imported candidates so the pool does not retry
    the same low-quality term forever.
    """
    if not keyword or not getattr(keyword,'source','').startswith('collector:'):
        return {'applied':False,'reason':'not_collector_keyword'}
    good=label in {'Action','Watch'}
    bad=label in {'Reject','Block'}
    if not (good or bad):
        return {'applied':False,'reason':'neutral_label'}
    source=keyword.source.removeprefix('collector:')
    delta={'Action':0.18,'Watch':0.06,'Reject':-0.16,'Block':-0.35}.get(label,0.0)
    weights=_collector_source_weights(db)
    entry=weights.get(source,{}) if isinstance(weights.get(source,{}),dict) else {}
    entry['weight']=round(max(0.25, min(2.5, float(entry.get('weight',1.0))+delta)), 3)
    stats=entry.setdefault('stats',{})
    stats[label]=int(stats.get(label,0))+1
    entry['last_keyword']=keyword.query
    entry['last_label']=label
    weights[source]=entry
    _save_collector_source_weights(db, weights)

    matched=_match_imported_candidates_for_keyword(db, keyword.query, keyword.source)
    domains=[]
    for cand, ev in matched:
        stats=ev.setdefault('feedback_stats',{})
        stats[label]=int(stats.get(label,0))+1
        ev['last_feedback_label']=label
        ev['last_feedback_at']=datetime.utcnow().isoformat(timespec='seconds')
        if good:
            cand.score=max(cand.score or 0, min(1.0, (cand.score or 0)+0.12))
            cand.status='promoted'
        elif bad:
            cand.score=max(0.0, (cand.score or 0)-0.25)
            cand.status='rejected'
            ev['reject_reason']='feedback_'+label.lower()
        if cand.source_domain:
            domains.append(cand.source_domain)
        cand.evidence_json=json.dumps(ev, ensure_ascii=False)
        db.merge(cand)

    # Learn seeds/domains from reviewed collector outputs. Keep this conservative:
    # good collector keywords become auto seeds; Block removes them and adds them to blocked terms.
    seed_row=db.get(models.Setting,'COLLECTOR_AUTO_SEEDS') or models.Setting(key='COLLECTOR_AUTO_SEEDS', value='', secret=False)
    seeds=[x.strip() for x in re.split(r'[\n,]+', seed_row.value or '') if x.strip()]
    domain_row=db.get(models.Setting,'COLLECTOR_AUTO_DOMAINS') or models.Setting(key='COLLECTOR_AUTO_DOMAINS', value='', secret=False)
    auto_domains=[x.strip() for x in re.split(r'[\n,]+', domain_row.value or '') if x.strip()]
    if good:
        if keyword.query not in seeds:
            seeds.append(keyword.query)
        for d in domains:
            if d and d not in auto_domains:
                auto_domains.append(d)
    elif bad:
        seeds=[s for s in seeds if s != keyword.query]
        if label == 'Block':
            blocked=[t.strip() for t in services.setting(db,'BLOCKED_TERMS').split(',') if t.strip()]
            blocked.append(keyword.query)
            row=db.get(models.Setting,'BLOCKED_TERMS') or models.Setting(key='BLOCKED_TERMS', value='', secret=False)
            row.value=','.join(sorted(set(blocked)))
            row.secret=False
            db.merge(row)
    seed_row.value=','.join(seeds[:80]); seed_row.secret=False; db.merge(seed_row)
    domain_row.value='\n'.join(auto_domains[:80]); domain_row.secret=False; db.merge(domain_row)
    db.commit()
    return {'applied':True,'source':source,'label':label,'matched_candidates':len(matched),'source_weight':weights[source]['weight'],'seed_count':len(seeds),'domain_count':len(auto_domains)}

def _split_setting_list(value:str)->list[str]:
    return [x.strip() for x in re.split(r"[\n,]+", value or '') if x.strip()]

def run_collector_autopilot(db:Session, limit:int=24, import_limit:int=12)->dict:
    """Run the free-first collector layer before Four-Find/SEO.

    This implements the article-group flow as automation, not a manual page:
    new pages / suggest terms / advanced SERP variants / source radar all land
    in candidate_keywords, then are cleaned and imported into keywords.
    """
    if (services.setting(db,'COLLECTOR_AUTO_ENABLED') or 'false').lower() not in {'1','true','yes','on'}:
        return {'enabled':False,'skipped':'COLLECTOR_AUTO_ENABLED=false','summary':collector_pool_summary(db)}
    seeds=_split_setting_list(services.setting(db,'COLLECTOR_AUTO_SEEDS'))
    domains=_split_setting_list(services.setting(db,'COLLECTOR_AUTO_DOMAINS'))
    try:
        max_seconds=int(services.setting(db,'COLLECTOR_AUTOPILOT_MAX_SECONDS') or '120')
    except Exception:
        max_seconds=120
    started=time.monotonic()
    def budget_left() -> bool:
        return time.monotonic() - started <= max_seconds
    plan=collector_budget_plan(db, limit=limit)
    results=[]
    errors=[]
    active={row['key']:row for row in plan.get('active',[])}
    if seeds and 'suggest' in active and budget_left():
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_suggest_collector(db, seeds[:active['suggest']['item_limit']], max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_SUGGEST_MAX_SECONDS') or '20'))))
        except Exception as e: errors.append({'collector':'suggest','error':str(e)[:180]})
    if domains and 'sitemap' in active and budget_left():
        try: results.append(run_sitemap_watcher(db, domains[:active['sitemap']['item_limit']], max_urls_per_domain=active['sitemap'].get('max_urls_per_domain', max(20,min(120,limit*4))), only_new=True))
        except Exception as e: errors.append({'collector':'sitemap','error':str(e)[:180]})
    if seeds and 'advanced_search' in active and budget_left():
        roots=seeds[:active['advanced_search']['item_limit']]
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_advanced_search_collector(db, roots, domains[:6], days=45, limit_per_query=active['advanced_search'].get('limit_per_query',5), max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_ADVANCED_MAX_SECONDS') or '90'))))
        except Exception as e: errors.append({'collector':'advanced_search','error':str(e)[:180]})
    if seeds and 'source_radar' in active and budget_left():
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_source_radar(db, seeds[:active['source_radar']['item_limit']], limit_per_seed=active['source_radar'].get('limit_per_seed',6), max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_SOURCE_RADAR_MAX_SECONDS') or '45'))))
        except Exception as e: errors.append({'collector':'source_radar','error':str(e)[:180]})
    if not budget_left():
        errors.append({'collector':'autopilot','error':f'time_budget_exceeded>{max_seconds}s'})
    clean=clean_candidate_pool(db, limit=max(200, limit*10))
    imported=import_candidates_to_keywords(db, limit=max(1, import_limit))
    return {'enabled':True,'seeds':seeds,'domains':domains,'budget_plan':plan,'results':results,'errors':errors[:20],'clean':clean,'import':imported,'summary':collector_pool_summary(db)}

from datetime import timedelta

def _candidate_from_search_result(item:dict)->str:
    title=item.get('title') or ''
    url=item.get('url') or item.get('link') or ''
    kw=keyword_from_url(url)
    title_kw=normalize_keyword(title)
    # Prefer URL slug when it looks specific; otherwise title.
    if kw and len(kw.split())>=2:
        return kw
    return title_kw

def run_advanced_search_collector(db:Session, roots:list[str], domains:list[str]|None=None, days:int=30, limit_per_query:int=8, max_seconds:int|None=None)->dict:
    """Article method: advanced search demand discovery.

    Generates allintitle/site/date variants and uses the configured SERP provider
    rotation (SearXNG/SerpApi/Zenserp/ScaleSERP/Brave/Tavily). Results are not
    treated as opportunities; title/URL terms are normalized into candidate pool.
    """
    domains=domains or []
    after=(datetime.utcnow()-timedelta(days=max(1,days))).date().isoformat()
    queries=[]
    for root in [r.strip() for r in roots if r.strip()]:
        queries.append((f'allintitle:"{root}" after:{after}', root, 'allintitle_after'))
        queries.append((f'"{root}" -site:.gov -site:wikipedia.org after:{after}', root, 'fresh_non_gov'))
        for d in domains[:10]:
            queries.append((f'site:{d.strip()} "{root}" after:{after}', root, 'site_after'))
    providers=services.available_serp_providers(db)
    try:
        max_seconds = int(max_seconds if max_seconds is not None else (services.setting(db,'COLLECTOR_ADVANCED_MAX_SECONDS') or '90'))
    except Exception:
        max_seconds = 90
    started=time.monotonic()
    saved=0; seen=0; errors=[]
    for q,root,variant in queries[:80]:
        if time.monotonic() - started > max_seconds:
            errors.append({'query':q,'error':f'time_budget_exceeded>{max_seconds}s'})
            break
        provider_used=''
        items=[]
        for p in providers[:max(1, int(services.setting(db,'SERP_PROVIDER_ATTEMPT_LIMIT') or '3'))]:
            if time.monotonic() - started > max_seconds:
                break
            provider_used=p
            try:
                res=services.provider_search(db,p,q,limit=limit_per_query)
            except Exception as e:
                errors.append({'query':q,'provider':p,'error':str(e)[:180]})
                continue
            if res and res[0].get('engine')!='error':
                items=res; break
        if not items:
            errors.append({'query':q,'error':'no results'})
            continue
        for item in items:
            kw=_candidate_from_search_result(item)
            if not kw: continue
            seen+=1
            url=item.get('url') or item.get('link') or ''
            row=upsert_candidate(db, kw, 'advanced_search', url, domain_of(url), '高级搜索找需求', {'query':q,'root':root,'variant':variant,'provider':provider_used,'title':item.get('title',''),'url':url}, 0.58)
            if row: saved+=1
    db.commit()
    return {'ok':True,'source':'advanced_search','queries':len(queries),'providers':providers,'candidates_seen':seen,'saved':saved,'errors':errors[:20]}

def run_source_radar(db:Session, seeds:list[str], limit_per_seed:int=10, max_seconds:int|None=None)->dict:
    """Article method: trace demand to early information sources.

    Free-first sources: Hacker News Algolia and arXiv. GitHub/HF can join later
    through the same candidate pool.
    """
    try:
        max_seconds = int(max_seconds if max_seconds is not None else (services.setting(db,'COLLECTOR_SOURCE_RADAR_MAX_SECONDS') or '45'))
    except Exception:
        max_seconds = 45
    started=time.monotonic()
    saved=0; seen=0; errors=[]
    for seed in [s.strip() for s in seeds if s.strip()]:
        if time.monotonic() - started > max_seconds:
            errors.append({'source':'source_radar','seed':seed,'error':f'time_budget_exceeded>{max_seconds}s'})
            break
        # HN Algolia
        try:
            if time.monotonic() - started > max_seconds:
                break
            r=requests.get('https://hn.algolia.com/api/v1/search_by_date', params={'query':seed,'tags':'story','hitsPerPage':limit_per_seed}, timeout=12)
            r.raise_for_status(); data=r.json()
            for h in data.get('hits',[])[:limit_per_seed]:
                title=h.get('title') or h.get('story_title') or ''
                url=h.get('url') or h.get('story_url') or ''
                kw=normalize_keyword(title)
                if kw:
                    seen+=1
                    row=upsert_candidate(db, kw, 'hn_algolia', url, domain_of(url), '信息溯源', {'seed':seed,'title':title,'hn_object_id':h.get('objectID')}, 0.50)
                    if row: saved+=1
        except Exception as e:
            errors.append({'source':'hn','seed':seed,'error':str(e)[:180]})
        # arXiv Atom feed (no key)
        try:
            if time.monotonic() - started > max_seconds:
                break
            r=requests.get('http://export.arxiv.org/api/query', params={'search_query':f'all:{seed}','sortBy':'submittedDate','sortOrder':'descending','max_results':limit_per_seed}, timeout=15)
            r.raise_for_status(); text=r.text
            titles=re.findall(r'<title>\s*([^<]+?)\s*</title>', text, flags=re.I|re.S)
            links=re.findall(r'<id>\s*([^<]+?)\s*</id>', text, flags=re.I|re.S)
            for i,title in enumerate(titles[1:limit_per_seed+1]): # first title is feed title
                title=re.sub(r'\s+',' ',title).strip()
                kw=normalize_keyword(title)
                if kw:
                    seen+=1
                    url=links[i+1] if i+1 < len(links) else ''
                    row=upsert_candidate(db, kw, 'arxiv', url, 'arxiv.org', '信息溯源', {'seed':seed,'title':title}, 0.48)
                    if row: saved+=1
        except Exception as e:
            errors.append({'source':'arxiv','seed':seed,'error':str(e)[:180]})
    db.commit()
    return {'ok':True,'source':'source_radar','seeds':len(seeds),'candidates_seen':seen,'saved':saved,'errors':errors[:20]}
