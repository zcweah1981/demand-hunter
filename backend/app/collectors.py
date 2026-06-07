from __future__ import annotations
import gzip, io, json, re
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote
import requests
from sqlalchemy.orm import Session
from . import models

STOPWORDS={"best","top","free","online","app","apps","software","tool","tools","page","blog","pricing","login","signup","about","contact","privacy","terms","docs","help","features"}

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
    terms=[t for t in s.split() if t not in STOPWORDS]
    if len(terms)<2: return ''
    return ' '.join(terms[:8])

def upsert_candidate(db:Session, keyword:str, source:str, source_url:str='', source_domain:str='', method:str='', evidence:dict|None=None, score:float=0.0):
    kw=normalize_keyword(keyword)
    if not kw: return None
    q=db.query(models.CandidateKeyword).filter_by(keyword=kw, source=source, source_url=source_url or '').first()
    if q:
        q.score=max(q.score, score)
        q.evidence_json=json.dumps({**(json.loads(q.evidence_json or '{}') if q.evidence_json else {}), **(evidence or {})}, ensure_ascii=False)
        db.merge(q); return q
    row=models.CandidateKeyword(keyword=kw, source=source, source_url=source_url or '', source_domain=source_domain or '', method=method, evidence_json=json.dumps(evidence or {}, ensure_ascii=False), score=score, status='new')
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

def run_sitemap_watcher(db:Session, domains:list[str], max_urls_per_domain=80)->dict:
    total=0; imported=0; errors=[]
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
                if kw:
                    total+=1
                    row=upsert_candidate(db, kw, 'sitemap', url, domain_of(url), '站找词', {'url':url}, 0.62)
                    if row: imported+=1
        except Exception as e:
            errors.append({'domain':d,'error':str(e)[:180]})
    db.commit()
    return {'ok':True,'source':'sitemap','domains':len(domains),'candidates_seen':total,'saved':imported,'errors':errors[:20]}

def suggest_queries(seed:str)->list[dict]:
    out=[]
    seed=seed.strip()
    if not seed: return out
    endpoints=[
        ('duckduckgo', 'https://duckduckgo.com/ac/', {'q':seed,'type':'list'}),
        ('google_suggest', 'https://suggestqueries.google.com/complete/search', {'client':'firefox','q':seed,'hl':'en'}),
    ]
    for source,url,params in endpoints:
        try:
            r=requests.get(url, params=params, headers={'User-Agent':'Mozilla/5.0'}, timeout=12)
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

def run_suggest_collector(db:Session, seeds:list[str])->dict:
    saved=0; seen=0
    for seed in seeds:
        for item in suggest_queries(seed):
            seen+=1
            row=upsert_candidate(db, item['keyword'], item['source'], '', '', '词找词', {'seed':seed,'provider':item['source']}, 0.55)
            if row: saved+=1
    db.commit()
    return {'ok':True,'source':'suggest','seeds':len(seeds),'candidates_seen':seen,'saved':saved}

def import_candidates_to_keywords(db:Session, limit:int=30)->dict:
    rows=db.query(models.CandidateKeyword).filter_by(status='new').order_by(models.CandidateKeyword.score.desc(), models.CandidateKeyword.created_at.desc()).limit(limit).all()
    imported=0
    for c in rows:
        existing=db.query(models.Keyword).filter_by(query=c.keyword).first()
        if not existing:
            db.add(models.Keyword(query=c.keyword, source=f'collector:{c.source}', root_terms='[]', score=c.score, status='new'))
            imported+=1
        c.status='imported'
        db.merge(c)
    db.commit()
    return {'ok':True,'selected':len(rows),'imported':imported}

from datetime import timedelta
from . import services

def _candidate_from_search_result(item:dict)->str:
    title=item.get('title') or ''
    url=item.get('url') or item.get('link') or ''
    kw=keyword_from_url(url)
    title_kw=normalize_keyword(title)
    # Prefer URL slug when it looks specific; otherwise title.
    if kw and len(kw.split())>=2:
        return kw
    return title_kw

def run_advanced_search_collector(db:Session, roots:list[str], domains:list[str]|None=None, days:int=30, limit_per_query:int=8)->dict:
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
    saved=0; seen=0; errors=[]
    for q,root,variant in queries[:80]:
        provider_used=''
        items=[]
        for p in providers[:max(1, int(services.setting(db,'SERP_PROVIDER_ATTEMPT_LIMIT') or '3'))]:
            provider_used=p
            res=services.provider_search(db,p,q,limit=limit_per_query)
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
            row=upsert_candidate(db, kw, 'advanced_search', url, domain_of(url), '高级搜索找需求', {'query':q,'root':root,'variant':variant,'provider':provider_used,'title':item.get('title','')}, 0.58)
            if row: saved+=1
    db.commit()
    return {'ok':True,'source':'advanced_search','queries':len(queries),'providers':providers,'candidates_seen':seen,'saved':saved,'errors':errors[:20]}

def run_source_radar(db:Session, seeds:list[str], limit_per_seed:int=10)->dict:
    """Article method: trace demand to early information sources.

    Free-first sources: Hacker News Algolia and arXiv. GitHub/HF can join later
    through the same candidate pool.
    """
    saved=0; seen=0; errors=[]
    for seed in [s.strip() for s in seeds if s.strip()]:
        # HN Algolia
        try:
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
