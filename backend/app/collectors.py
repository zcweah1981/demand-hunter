from __future__ import annotations
import gzip, html, io, json, re, time
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote
import requests
from sqlalchemy.orm import Session
from . import models, services

STOPWORDS={"best","top","free","online","app","apps","software","tool","tools","page","blog","blogs","pricing","login","signup","about","contact","privacy","terms","docs","help","features","category","tag","author","news","article","post","posts","product","products","with","using","without","guide","guides","definition","meaning","en","pt","de","fr","es","it","nl","pl","www","youtube","reddit","github"}
TOOL_INTENT_TERMS={"calculator","generator","template","checker","converter","tracker","dashboard","analyzer","builder","creator","planner","estimator","form","spreadsheet","invoice","policy","report","monitor","automation","integration","api","alternative"}
TOOL_INTENT_PLURALS={"calculators":"calculator","generators":"generator","templates":"template","checkers":"checker","converters":"converter","trackers":"tracker","tracking":"tracker","dashboards":"dashboard","analyzers":"analyzer","builders":"builder","planners":"planner","estimators":"estimator","forms":"form","spreadsheets":"spreadsheet","reports":"report","monitors":"monitor","automations":"automation","integrations":"integration","apis":"api","alternatives":"alternative"}
COMMERCIAL_TERMS={"pricing","price","cost","fee","invoice","tax","compliance","shopify","woocommerce","quickbooks","hubspot","salesforce","stripe","paypal","b2b","business","agency","client","contractor","clinic","rental"}
EARLY_SOURCE_BONUS={"sitemap":0.16,"advanced_search":0.12,"hn_algolia":0.10,"arxiv":0.08,"google_suggest":0.06,"duckduckgo":0.05}
NOISE_DOMAINS={"github.com","raw.githubusercontent.com","gist.github.com"}
NOISE_TITLE_PATTERNS=(
    r"\bpull request\b", r"\bissue\b", r"\bcommit\b", r"\bmerge pull request\b",
    r"\bfix\b.*\b(generator|bug|test|ci|build)\b", r"\battempt to\b",
    r"\blabels?\b", r"\bmilestone\b", r"\brelease notes?\b", r"\bchangelog\b",
    r"\bdocumentation\b", r"\bdocs?\b", r"\breadme\b",
)
BLOCK_TARGET_DOMAINS={"google.com","youtube.com","wikipedia.org","reddit.com","facebook.com","linkedin.com","x.com","twitter.com","github.com","support.google.com","dictionary.com","merriam-webster.com","dictionary.cambridge.org","bestbuy.com","bestwestern.com","alternativeto.net","pinterest.com","capitalone.com","card.com","creditcards.chase.com","usafacts.org","apps.microsoft.com","play.google.com"}
TECH_SOURCE_RADAR_TERMS={"ai","llm","rag","mcp","agent","agents","model","models","openai","anthropic","claude","gemini","vector","embedding","eval","benchmark","inference","gpu","workflow automation"}
SHORT_TAIL_REWRITE_BAD_TERMS={"branding","history","quote","quotes","signature","signatures","receipt","receipts","settings","account","login","signup","profile","community","communities","competitor","competitors","auditor","auditors","forum","forums"}
def is_blocked_domain(domain:str)->bool:
    d=(domain or '').lower().removeprefix('www.')
    return any(d==b or d.endswith('.'+b) for b in BLOCK_TARGET_DOMAINS)

def _target_topic(text:str)->str:
    kw=normalize_keyword(text)
    return ' '.join(kw.split()[:4]) if kw else (text or '')[:80]

def _upsert_collector_target(db:Session, target_type:str, value:str, source_type:str, source_id:str, topic:str, priority:float, notes:str=""):
    value=(value or '').strip().lower()
    if not value: return None
    if target_type=='keyword':
        value=normalize_keyword(value)
        if not value or candidate_noise_reason(value): return None
    if target_type=='domain':
        value=value.removeprefix('www.')
        if is_blocked_domain(value) or any(value.endswith('.gov') for _ in [0]): return None
    source_id=str(source_id)
    for obj in list(db.new):
        if isinstance(obj, models.CollectorTarget) and obj.target_type==target_type and obj.value==value and obj.source_type==source_type and str(obj.source_id)==source_id:
            obj.priority=max(obj.priority or 0, priority)
            return obj
    with db.no_autoflush:
        row=db.query(models.CollectorTarget).filter_by(target_type=target_type,value=value,source_type=source_type,source_id=source_id).first()
    if not row:
        row=models.CollectorTarget(target_type=target_type,value=value,source_type=source_type,source_id=str(source_id),topic=topic[:160],priority=priority,status='active',notes=notes[:800])
        db.add(row)
    else:
        row.priority=max(row.priority or 0, priority)
        row.status='active' if row.status in {'exhausted','cooldown'} and priority>=75 else row.status
        row.notes=notes[:800] or row.notes
    return row

def _keyword_variants_from_text(text:str)->list[str]:
    text=(text or '').lower()
    base=normalize_keyword(text)
    variants=[]
    if base: variants.append(base)
    # Compliance-specific expansion: current cards prove this is a viable cluster.
    if 'compliance' in text:
        for fw in ['soc 2','gdpr','hipaa','iso 27001','pci']:
            for tail in ['compliance cost calculator','compliance gap analysis','readiness calculator','compliance checklist template']:
                variants.append(f'{fw} {tail}')
        variants.extend(['compliance roi calculator','compliance cost calculator','compliance gap analysis tool'])
    if 'shopify' in text and 'tax' in text:
        variants.extend(['shopify sales tax api','shopify tax calculator','shopify sales tax compliance','shopify tax app alternatives'])
    if 'invoice' in text:
        variants.extend(['invoice generator','invoice calculator','invoice late fee calculator','invoice payment reminder template'])
    if 'rental' in text or 'late fee notice' in text:
        variants.extend(['rental late fee notice template','late rent notice template','past due rent notice template'])
    out=[]
    for v in variants:
        nv=normalize_keyword(v)
        if re.match(r"^\d+\b", nv): continue
        if re.search(r"\b(tractian|symmetry|security compass|invoiceflow|zogby|sprinto|easyaudit)\b$", nv): continue
        if len(nv.split()) > 6 and not any(t in nv for t in ['calculator','template','checker','tracker','generator','dashboard']): continue
        if nv and nv not in out and not candidate_noise_reason(nv): out.append(nv)
    return out[:24]

def expand_generic_short_tail(keyword:str)->list[str]:
    """Rewrite short generic heads into executable long-tail task queries."""
    kw=normalize_keyword(keyword)
    if not kw: return []
    terms=set(kw.split())
    raw_terms=set(re.split(r"\s+", (keyword or '').lower().strip()))
    if raw_terms & SHORT_TAIL_REWRITE_BAD_TERMS:
        return []
    if any(len(t)<=2 and t not in {'ai'} for t in raw_terms):
        return []
    variants=[]
    if 'shopify' in terms and 'tax' in terms:
        variants += ['shopify sales tax calculator','shopify tax compliance checklist','shopify sales tax api','shopify tax app alternatives']
    if 'compliance' in terms and ('tracker' in terms or 'tracking' in terms):
        variants += ['vendor compliance tracker template','compliance audit tracker template','compliance evidence tracker','compliance automation tracker']
    if 'compliance' in terms and 'calculator' in terms:
        variants += ['compliance cost calculator','compliance roi calculator','soc 2 compliance cost calculator','gdpr compliance cost calculator','hipaa compliance cost calculator']
    if 'invoice' in terms and 'calculator' in terms:
        variants += ['invoice total calculator','invoice late fee calculator','invoice payment terms calculator','invoice tax calculator template']
    if 'vendor' in terms and 'compliance' in terms:
        variants += ['vendor compliance checklist template','vendor compliance tracker','vendor risk assessment checklist','vendor compliance audit template']
    if not variants and len(terms)<=2:
        variants += [f'{kw} template', f'{kw} calculator', f'{kw} checklist', f'{kw} tracker']
    out=[]
    for v in variants:
        nv=normalize_keyword(v)
        if nv and nv!=kw and nv not in out and not candidate_noise_reason(nv): out.append(nv)
    return out[:12]

def refresh_collector_targets_from_cards(db:Session, limit:int=80)->dict:
    """Generate collector targets from Action/Watch cards and their SERP evidence.

    This is the automation bridge: opportunity cards and competitor domains become
    the next collector inputs without manual settings edits.
    """
    cards=db.query(models.OpportunityCard).filter(models.OpportunityCard.verdict.in_(['Action','Watch'])).order_by(models.OpportunityCard.score.desc()).limit(limit).all()
    created=0; keyword_targets=0; domain_targets=0
    seen_targets:set[tuple[str,str,str,str]]=set()
    for card in cards:
        kw=db.get(models.Keyword, card.keyword_id)
        if not kw: continue
        verdict_boost=35 if card.verdict=='Action' else 18
        base_priority=min(100.0, float(card.score or 0)+verdict_boost)
        topic=_target_topic(kw.query)
        texts=[kw.query, card.title or '', card.mvp_plan or '']
        try:
            evidence=json.loads(card.evidence_json or '[]')
        except Exception:
            evidence=[]
        for e in evidence:
            if isinstance(e,dict):
                texts.append(str(e.get('title') or ''))
                url=e.get('url') or ''
                d=domain_of(url)
                if d and not is_blocked_domain(d):
                    key=('domain',d,'opportunity_card',str(card.id))
                    if key in seen_targets: continue
                    seen_targets.add(key)
                    row=_upsert_collector_target(db,'domain',d,'opportunity_card',str(card.id),topic,base_priority-5,f'from card #{card.id} SERP/evidence: {kw.query}')
                    if row: domain_targets+=1; created+=1
        # also use stored SERP rows because evidence_json can be sparse.
        for serp in db.query(models.SerpResult).filter_by(keyword_id=kw.id).order_by(models.SerpResult.rank).limit(10):
            d=(serp.domain or domain_of(serp.url or '')).lower().removeprefix('www.')
            if d and not is_blocked_domain(d):
                key=('domain',d,'opportunity_card',str(card.id))
                if key in seen_targets: continue
                seen_targets.add(key)
                row=_upsert_collector_target(db,'domain',d,'opportunity_card',str(card.id),topic,base_priority-8,f'from card #{card.id} SERP rank {serp.rank}: {kw.query}')
                if row: domain_targets+=1; created+=1
            texts.append(serp.title or '')
        for text in texts:
            for v in _keyword_variants_from_text(text):
                key=('keyword',v,'opportunity_card',str(card.id))
                if key in seen_targets: continue
                seen_targets.add(key)
                row=_upsert_collector_target(db,'keyword',v,'opportunity_card',str(card.id),topic,base_priority,f'from card #{card.id}: {kw.query}')
                if row: keyword_targets+=1; created+=1
    db.commit()
    return {'ok':True,'cards_scanned':len(cards),'targets_touched':created,'keyword_targets':keyword_targets,'domain_targets':domain_targets}

def select_collector_targets(db:Session, target_type:str, limit:int=20)->list[models.CollectorTarget]:
    return db.query(models.CollectorTarget).filter_by(target_type=target_type,status='active').order_by(models.CollectorTarget.priority.desc(), models.CollectorTarget.created_at.desc()).limit(limit).all()

def _touch_collector_target(db:Session, target_type:str, value:str, success:bool=False, reject:bool=False)->None:
    value=(value or '').strip().lower().removeprefix('www.')
    if not value: return
    with db.no_autoflush:
        rows=db.query(models.CollectorTarget).filter_by(target_type=target_type,value=value,status='active').limit(20).all()
    now=datetime.utcnow()
    for t in rows:
        t.last_seen_at=now
        if success:
            t.success_count=(t.success_count or 0)+1
            t.last_success_at=now
            t.priority=min(100.0, (t.priority or 0)+2.0)
        if reject:
            t.reject_count=(t.reject_count or 0)+1
            if (t.reject_count or 0)>=5 and not (t.success_count or 0):
                t.status='cooldown'
        db.merge(t)

def apply_collector_target_health(db:Session)->dict:
    """Apply lightweight target lifecycle: promote productive targets, cooldown noisy ones."""
    rows=db.query(models.CollectorTarget).filter(models.CollectorTarget.status.in_(['active','cooldown'])).all()
    cooled=0; promoted=0; active=0
    for t in rows:
        success=t.success_count or 0
        reject=t.reject_count or 0
        if t.status=='active' and reject >= 8 and success == 0:
            t.status='cooldown'; t.notes=((t.notes or '') + ' | auto cooldown: reject>=8 success=0')[:800]; cooled+=1
        elif t.status=='active' and reject >= 12 and reject >= success*4:
            t.status='cooldown'; t.notes=((t.notes or '') + f' | auto cooldown: reject={reject} success={success}')[:800]; cooled+=1
        elif t.status=='cooldown' and success >= 2:
            t.status='active'; promoted+=1
        if t.status=='active': active+=1
        db.merge(t)
    db.commit()
    return {'ok':True,'scanned':len(rows),'cooled':cooled,'promoted':promoted,'active':active}

def collector_target_segments(db:Session, limit:int=200)->dict:
    """Segment targets for budget decisions and operator review."""
    rows=db.query(models.CollectorTarget).order_by(models.CollectorTarget.priority.desc(), models.CollectorTarget.created_at.desc()).limit(limit).all()
    out={'winner':[],'promising':[],'noisy':[],'exhausted':[],'cooldown':[],'new':[]}
    seen_values=set()
    for t in rows:
        value_key=(t.target_type,t.value,t.status)
        if value_key in seen_values:
            continue
        seen_values.add(value_key)
        success=t.success_count or 0
        reject=t.reject_count or 0
        priority=t.priority or 0
        item={'id':t.id,'target_type':t.target_type,'value':t.value,'topic':t.topic,'priority':priority,'status':t.status,'success_count':success,'reject_count':reject,'last_seen_at':t.last_seen_at.isoformat() if t.last_seen_at else None,'last_success_at':t.last_success_at.isoformat() if t.last_success_at else None,'notes':t.notes}
        if t.status=='cooldown':
            out['cooldown'].append(item)
        elif t.status in {'rejected','exhausted'}:
            out['exhausted'].append(item)
        elif success >= 3 and priority >= 85 and reject <= max(3, success*2):
            out['winner'].append(item)
        elif reject >= 8 and success == 0:
            out['noisy'].append(item)
        elif reject >= 12 and reject >= success*4:
            out['noisy'].append(item)
        elif success > 0 or priority >= 80:
            out['promising'].append(item)
        else:
            out['new'].append(item)
    summary={k:len(v) for k,v in out.items()}
    return {'ok':True,'summary':summary,'segments':out}

def collector_next_budget(db:Session, limit:int=24)->dict:
    """Preview next collector budget allocation before a run."""
    seg=collector_target_segments(db, limit=300)
    base_weights={'winner':0.40,'promising':0.38,'new':0.14,'manual':0.08,'noisy':0.0,'cooldown':0.0,'exhausted':0.0}
    weights=dict(base_weights)
    adjustment_log=[]
    # Conservative ROI-driven adjustment. Segment ROI nudges target budget but
    # never fully overrides the base exploration mix; this prevents one lucky
    # short run from collapsing discovery diversity.
    try:
        roi=collector_roi_stats(db, limit=12)
        roi_rows={r['segment']:r for r in roi.get('by_segment',[])}
        verdicts={k:r['verdict'] for k,r in roi_rows.items()}
        for key in ['winner','promising','new']:
            row=roi_rows.get(key,{})
            before=weights[key]
            if verdicts.get(key)=='increase':
                weights[key]+=0.08
                adjustment_log.append({'scope':'segment','key':key,'action':'increase','before':before,'after_raw':weights[key],'reason':f"verdict=increase avg_success={row.get('avg_success')} avg_reject={row.get('avg_reject')} avg_priority={row.get('avg_priority')}"})
            elif verdicts.get(key)=='decrease':
                weights[key]=max(0.03, weights[key]-0.10)
                adjustment_log.append({'scope':'segment','key':key,'action':'decrease','before':before,'after_raw':weights[key],'reason':f"verdict=decrease avg_success={row.get('avg_success')} avg_reject={row.get('avg_reject')} avg_priority={row.get('avg_priority')}"})
        if verdicts.get('winner')=='increase' and verdicts.get('promising')!='increase':
            before=weights['promising']
            weights['promising']=max(0.20, weights['promising']-0.05)
            adjustment_log.append({'scope':'segment','key':'promising','action':'rebalance_to_winner','before':before,'after_raw':weights['promising'],'reason':'winner=increase while promising is not increase'})
        total=sum(weights[k] for k in ['winner','promising','new','manual']) or 1.0
        for key in ['winner','promising','new','manual']:
            before=weights[key]
            weights[key]=round(weights[key]/total, 3)
            if before != weights[key]:
                adjustment_log.append({'scope':'segment','key':key,'action':'normalize','before':before,'after':weights[key],'reason':f'normalize total={round(total,3)}'})
    except Exception:
        weights=base_weights
        adjustment_log.append({'scope':'segment','key':'*','action':'fallback','reason':'ROI adjustment failed; using base weights'})
    allocation=[]
    used=0
    for key,label in [('winner','Winner targets'),('promising','Promising targets'),('new','New targets'),('manual','Manual fallback'),('noisy','Noisy targets'),('cooldown','Cooldown targets'),('exhausted','Exhausted/Rejected')]:
        count=len(seg['segments'].get(key,[])) if key!='manual' else len(_split_setting_list(services.setting(db,'COLLECTOR_AUTO_SEEDS')))+len(_split_setting_list(services.setting(db,'COLLECTOR_AUTO_DOMAINS')))
        budget=0 if weights[key]<=0 or count==0 else max(1, round(limit*weights[key]))
        used+=budget
        allocation.append({'segment':key,'label':label,'weight':weights[key],'base_weight':base_weights.get(key,0.0),'available':count,'budget':budget,'targets':(seg['segments'].get(key,[])[:50] if key!='manual' else [])})
    # Normalize if rounding exceeded limit; remove from lower priority positive buckets.
    overflow=max(0, used-limit)
    if overflow:
        for row in reversed(allocation):
            if row['segment'] in {'manual','new','promising'} and row['budget']>0 and overflow>0:
                take=min(row['budget'], overflow)
                row['budget']-=take; overflow-=take
    source_plan=collector_budget_plan(db, limit=limit)
    return {'ok':True,'limit':limit,'target_segments':seg['summary'],'allocation':allocation,'source_plan':source_plan,'roi_adjusted':weights!=base_weights,'adjustment_log':adjustment_log}

def collector_roi_stats(db:Session, limit:int=12)->dict:
    """Aggregate recent collector_autopilot replay history into source/segment ROI."""
    rows=db.query(models.RunHistory).filter_by(kind='collector_autopilot').order_by(models.RunHistory.started_at.desc()).limit(max(1,min(50,limit))).all()
    by_source={}; by_segment={}; runs=[]
    for row in rows:
        try: s=json.loads(row.summary or '{}')
        except Exception: s={}
        runs.append({'id':row.id,'started_at':row.started_at.isoformat() if row.started_at else None,'imported':(s.get('import') or {}).get('imported',0),'selected':(s.get('import') or {}).get('selected',0)})
        for r in s.get('source_results') or []:
            key=r.get('source') or 'unknown'
            e=by_source.setdefault(key, {'source':key,'runs':0,'seen':0,'saved':0,'errors':0})
            e['runs']+=1; e['seen']+=int(r.get('seen') or 0); e['saved']+=int(r.get('saved') or 0); e['errors']+=int(r.get('errors') or 0)
        for seg, items in (s.get('selected_by_segment') or {}).items():
            e=by_segment.setdefault(seg, {'segment':seg,'runs':0,'targets':0,'success_sum':0,'reject_sum':0,'priority_sum':0.0})
            e['runs']+=1; e['targets']+=len(items or [])
            for t in items or []:
                e['success_sum']+=int(t.get('success') or 0); e['reject_sum']+=int(t.get('reject') or 0); e['priority_sum']+=float(t.get('priority') or 0)
    for e in by_source.values():
        e['save_rate']=round(e['saved']/max(1,e['seen']),3)
        e['error_rate']=round(e['errors']/max(1,e['runs']),3)
        if e['save_rate']>=0.25 and e['errors']<=max(2,e['runs']): e['verdict']='increase'
        elif e['save_rate']<0.05 and e['seen']>=20: e['verdict']='decrease'
        else: e['verdict']='watch'
    for e in by_segment.values():
        e['avg_success']=round(e['success_sum']/max(1,e['targets']),2)
        e['avg_reject']=round(e['reject_sum']/max(1,e['targets']),2)
        e['avg_priority']=round(e['priority_sum']/max(1,e['targets']),1)
        if e['avg_success']>=2 and e['avg_reject']<=e['avg_success']*2: e['verdict']='increase'
        elif e['avg_reject']>=5 and e['avg_success']==0: e['verdict']='decrease'
        else: e['verdict']='watch'
    return {'ok':True,'runs':runs,'by_source':sorted(by_source.values(), key=lambda x:(x['verdict']!='increase', -x['save_rate'], -x['saved'])),'by_segment':sorted(by_segment.values(), key=lambda x:(x['verdict']!='increase', -x['avg_success'], -x['avg_priority']))}

def collector_system_health(db:Session)->dict:
    """High-level collector health score for the dashboard."""
    seg=collector_target_segments(db, limit=300)
    roi=collector_roi_stats(db, limit=12)
    pool=collector_pool_summary(db)
    budget=collector_next_budget(db, limit=24)
    latest=db.query(models.RunHistory).filter_by(kind='collector_autopilot').order_by(models.RunHistory.started_at.desc()).first()
    issues=[]; strengths=[]; repairs=[]; score=100
    summary=seg.get('summary') or {}
    active=summary.get('winner',0)+summary.get('promising',0)+summary.get('new',0)
    noisy=summary.get('noisy',0)+summary.get('cooldown',0)+summary.get('exhausted',0)
    if active < 10:
        score-=18; issues.append({'code':'low_active_targets','severity':'warning','text':f'active usable targets only {active}'})
    else:
        strengths.append({'code':'target_pool_ready','text':f'{active} usable targets'})
    if summary.get('winner',0) == 0:
        score-=14; issues.append({'code':'no_winner_targets','severity':'warning','text':'no winner targets yet'})
    else:
        strengths.append({'code':'winner_targets','text':f"{summary.get('winner')} winner target(s)"})
    if noisy > max(8, active*0.25):
        score-=12; issues.append({'code':'too_many_bad_targets','severity':'warning','text':f'{noisy} noisy/cooldown/exhausted targets'})
    source_increase=sum(1 for r in roi.get('by_source',[]) if r.get('verdict')=='increase')
    source_decrease=sum(1 for r in roi.get('by_source',[]) if r.get('verdict')=='decrease')
    if source_increase:
        strengths.append({'code':'source_roi_positive','text':f'{source_increase} source(s) with increasing ROI'})
    if source_decrease:
        score-=10; issues.append({'code':'source_roi_negative','severity':'warning','text':f'{source_decrease} source(s) with decreasing ROI'})
    new_candidates=(pool.get('by_status') or {}).get('new',0)
    rejected=(pool.get('by_status') or {}).get('rejected',0)
    total=pool.get('total') or 0
    if total and rejected/max(1,total) > 0.75:
        score-=10; issues.append({'code':'candidate_reject_heavy','severity':'info','text':f'rejected candidates are {round(rejected/max(1,total)*100)}% of pool'})
        repairs.append({'id':'inspect_rejected_reasons','label':'查看 rejected reason 分布','safety':'只读','endpoint':'/api/collectors/rejected-reasons'})
        repairs.append({'id':'repair_missing_tool_intent','label':'修复 missing_tool_intent 噪音','safety':'可逆：调整 source 权重并开启 source_radar tech-only','endpoint':'/api/collectors/repairs/missing-tool-intent'})
        repairs.append({'id':'repair_generic_short_tail','label':'改写 generic_short_tail 短头词','safety':'可逆：新增 rewrite candidates，保留原 rejected','endpoint':'/api/collectors/repairs/generic-short-tail'})
        repairs.append({'id':'repair_sitemap_editorial_path','label':'修复 sitemap_editorial_path 噪音','safety':'可逆：仅将 sitemap editorial candidates 标记 rejected','endpoint':'/api/collectors/repairs/sitemap-editorial-path'})
        repairs.append({'id':'cleanup_old_rejected','label':'清理旧 rejected candidates','safety':'可逆性低：删除 rejected 候选记录，不影响 keywords/cards','endpoint':'/api/collectors/candidates/rejected/cleanup'})
    if new_candidates > 0:
        strengths.append({'code':'candidate_pool_has_work','text':f'{new_candidates} new candidates waiting'})
    if latest:
        try: s=json.loads(latest.summary or '{}')
        except Exception: s={}
        imported=(s.get('import') or {}).get('imported',0)
        if imported == 0:
            score-=10; issues.append({'code':'latest_run_no_imports','severity':'warning','text':'latest collector run imported 0 keywords'})
        else:
            strengths.append({'code':'latest_run_imported','text':f'latest run imported {imported} keyword(s)'})
    else:
        score-=12; issues.append({'code':'no_collector_runs','severity':'warning','text':'no collector autopilot run history yet'})
    if budget.get('roi_adjusted'):
        strengths.append({'code':'roi_budget_active','text':'ROI-adjusted budget is active'})
    score=max(0,min(100,score))
    if score>=80: status='healthy'
    elif score>=60: status='watch'
    else: status='needs_attention'
    return {'ok':True,'score':score,'status':status,'summary':{'usable_targets':active,'bad_targets':noisy,'new_candidates':new_candidates,'source_increase':source_increase,'source_decrease':source_decrease,'latest_run_id':latest.id if latest else None},'issues':issues,'strengths':strengths,'repairs':repairs,'target_segments':summary,'source_roi':roi.get('by_source',[])[:8]}

def rejected_candidate_reasons(db:Session, limit:int=500)->dict:
    rows=db.query(models.CandidateKeyword).filter_by(status='rejected').order_by(models.CandidateKeyword.created_at.desc()).limit(max(1,min(5000,limit))).all()
    by_reason={}; by_source={}; examples=[]
    for r in rows:
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        reason=ev.get('reject_reason') or 'unknown'
        by_reason[reason]=by_reason.get(reason,0)+1
        by_source[r.source or 'unknown']=by_source.get(r.source or 'unknown',0)+1
        if len(examples)<20:
            examples.append({'id':r.id,'keyword':r.keyword,'source':r.source,'reason':reason,'source_url':r.source_url})
    return {'ok':True,'scanned':len(rows),'by_reason':sorted([{'reason':k,'count':v} for k,v in by_reason.items()], key=lambda x:x['count'], reverse=True),'by_source':sorted([{'source':k,'count':v} for k,v in by_source.items()], key=lambda x:x['count'], reverse=True),'examples':examples}

def cleanup_rejected_candidates(db:Session, keep_latest:int=300)->dict:
    rows=db.query(models.CandidateKeyword).filter_by(status='rejected').order_by(models.CandidateKeyword.created_at.desc()).all()
    delete_rows=rows[max(0,keep_latest):]
    deleted=0
    for r in delete_rows:
        db.delete(r); deleted+=1
    db.commit()
    return {'ok':True,'kept':min(len(rows),keep_latest),'deleted':deleted,'total_rejected_before':len(rows)}

def apply_missing_tool_intent_repair(db:Session)->dict:
    """Reduce future missing_tool_intent noise by tightening source radar and demoting noisy sources."""
    dist=rejected_candidate_reasons(db, limit=1000)
    missing_by_source={}
    total_by_source={}
    for r in db.query(models.CandidateKeyword).filter_by(status='rejected').order_by(models.CandidateKeyword.created_at.desc()).limit(1000):
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        total_by_source[r.source or 'unknown']=total_by_source.get(r.source or 'unknown',0)+1
        if (ev.get('reject_reason') or '') == 'missing_tool_intent':
            missing_by_source[r.source or 'unknown']=missing_by_source.get(r.source or 'unknown',0)+1
    weights=_collector_source_weights(db)
    changes=[]
    for source,count in missing_by_source.items():
        total=total_by_source.get(source, count)
        if count >= 8 or count/max(1,total) >= 0.45:
            entry=weights.get(source,{}) if isinstance(weights.get(source,{}),dict) else {}
            old=float(entry.get('weight',1.0))
            new=round(max(0.25, old*0.82),3)
            if new != old:
                entry['weight']=new
                entry.setdefault('repair_stats',{})['missing_tool_intent_demoted_at']=datetime.utcnow().isoformat(timespec='seconds')
                entry['repair_stats']['missing_tool_intent_count']=count
                weights[source]=entry
                changes.append({'source':source,'old':old,'new':new,'missing_tool_intent':count,'rejected_total':total})
    _save_collector_source_weights(db, weights)
    row=db.get(models.Setting,'COLLECTOR_SOURCE_RADAR_TECH_ONLY') or models.Setting(key='COLLECTOR_SOURCE_RADAR_TECH_ONLY', value='true', secret=False)
    row.value='true'; row.secret=False; db.merge(row)
    audit={'changes':changes,'source_radar_tech_only':True,'top_reasons':dist.get('by_reason',[])[:8],'top_sources':dist.get('by_source',[])[:8]}
    db.add(models.RunHistory(kind='collector_repair', status='ok', summary=json.dumps({'repair':'missing_tool_intent','result':audit}, ensure_ascii=False), finished_at=datetime.utcnow()))
    db.commit()
    return {'ok':True, **audit}

def apply_generic_short_tail_repair(db:Session, limit:int=300)->dict:
    """Rewrite rejected generic short-tail candidates into concrete task variants."""
    rows=db.query(models.CandidateKeyword).filter_by(status='rejected').order_by(models.CandidateKeyword.created_at.desc()).limit(max(1,min(1000,limit))).all()
    scanned=0; rewritten=0; variants_saved=0; examples=[]
    for r in rows:
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        if ev.get('reject_reason') != 'generic_short_tail':
            continue
        scanned+=1
        variants=expand_generic_short_tail(r.keyword)
        if not variants: continue
        ev['rewrite_candidates']=variants
        r.evidence_json=json.dumps(ev, ensure_ascii=False)
        db.merge(r); rewritten+=1
        for v in variants:
            row=upsert_candidate(db, v, 'short_tail_rewrite', r.source_url, r.source_domain, '短头词改写', {**ev, 'original_keyword': r.keyword, 'rewrite_reason':'generic_short_tail'}, 0.57)
            if row: variants_saved+=1
        if len(examples)<10: examples.append({'original':r.keyword,'variants':variants})
    db.commit()
    audit={'scanned_generic_short_tail':scanned,'rewritten':rewritten,'variants_saved':variants_saved,'examples':examples}
    db.add(models.RunHistory(kind='collector_repair', status='ok', summary=json.dumps({'repair':'generic_short_tail','result':audit}, ensure_ascii=False), finished_at=datetime.utcnow()))
    db.commit()
    return {'ok':True, **audit}

def apply_sitemap_editorial_path_repair(db:Session, limit:int=500)->dict:
    """Move editorial sitemap URL-path candidates out of the importable pool."""
    rows=db.query(models.CandidateKeyword).filter(models.CandidateKeyword.source=='sitemap').order_by(models.CandidateKeyword.created_at.desc()).limit(max(1,min(2000,limit))).all()
    scanned=0; rejected=0; examples=[]
    for r in rows:
        scanned+=1
        if sitemap_url_is_task_page(r.source_url or ''):
            continue
        try: ev=json.loads(r.evidence_json or '{}')
        except Exception: ev={}
        ev['reject_reason']='sitemap_editorial_path'
        ev['repair_note']='URL path is editorial/blog/resource; use domain_web title/meta collector instead'
        r.status='rejected'
        r.evidence_json=json.dumps(ev, ensure_ascii=False)
        db.merge(r); rejected+=1
        if len(examples)<10: examples.append({'id':r.id,'keyword':r.keyword,'url':r.source_url})
    audit={'scanned':scanned,'rejected':rejected,'examples':examples,'sitemap_path_gate':'task_pages_only'}
    db.add(models.RunHistory(kind='collector_repair', status='ok', summary=json.dumps({'repair':'sitemap_editorial_path','result':audit}, ensure_ascii=False), finished_at=datetime.utcnow()))
    db.commit()
    return {'ok':True, **audit}

def collector_roi_weight_recommendations(db:Session, limit:int=12, min_runs:int=2)->dict:
    """Recommend persistent COLLECTOR_SOURCE_WEIGHTS changes from ROI.

    This is deliberately more conservative than per-run ROI budget nudges: it
    only becomes eligible after a source has appeared in at least min_runs
    replay records.
    """
    roi=collector_roi_stats(db, limit=limit)
    weights=_collector_source_weights(db)
    recs=[]
    for row in roi.get('by_source',[]):
        source=row['source']
        current=weights.get(source,{}).get('weight',1.0) if isinstance(weights.get(source,{}),dict) else 1.0
        try: current=float(current)
        except Exception: current=1.0
        eligible=row.get('runs',0) >= min_runs and row.get('verdict') in {'increase','decrease'}
        if row.get('verdict')=='increase': suggested=round(min(2.5, current+0.08),3)
        elif row.get('verdict')=='decrease': suggested=round(max(0.25, current-0.12),3)
        else: suggested=current
        recs.append({'source':source,'current_weight':round(current,3),'suggested_weight':suggested,'eligible':eligible,'verdict':row.get('verdict'),'runs':row.get('runs'), 'seen':row.get('seen'), 'saved':row.get('saved'), 'save_rate':row.get('save_rate'), 'errors':row.get('errors'), 'reason':f"verdict={row.get('verdict')} runs={row.get('runs')} saved/seen={row.get('saved')}/{row.get('seen')} save_rate={row.get('save_rate')}"})
    return {'ok':True,'min_runs':min_runs,'recommendations':recs}

def apply_collector_roi_weight_recommendations(db:Session, limit:int=12, min_runs:int=2)->dict:
    rec=collector_roi_weight_recommendations(db, limit=limit, min_runs=min_runs)
    weights=_collector_source_weights(db)
    applied=[]
    for r in rec.get('recommendations',[]):
        if not r.get('eligible') or r.get('suggested_weight') == r.get('current_weight'):
            continue
        entry=weights.get(r['source'],{}) if isinstance(weights.get(r['source'],{}),dict) else {}
        entry['weight']=r['suggested_weight']
        stats=entry.setdefault('roi_apply_stats',{})
        stats['last_verdict']=r.get('verdict')
        stats['last_reason']=r.get('reason')
        stats['last_applied_at']=datetime.utcnow().isoformat(timespec='seconds')
        weights[r['source']]=entry
        applied.append(r)
    if applied:
        _save_collector_source_weights(db, weights)
        db.add(models.RunHistory(kind='collector_roi_weights', status='ok', summary=json.dumps({'applied':applied,'min_runs':min_runs}, ensure_ascii=False), finished_at=datetime.utcnow()))
        db.commit()
    return {'ok':True,'applied_count':len(applied),'applied':applied,'recommendations':rec.get('recommendations',[])}

def select_budgeted_collector_targets(db:Session, limit:int=24)->dict:
    """Select unique targets according to the same segment budget preview."""
    budget=collector_next_budget(db, limit=limit)
    selected=[]; seen=set(); by_segment={}
    for row in budget.get('allocation',[]):
        seg=row['segment']; take=max(0, int(row.get('budget') or 0))
        if take <= 0 or seg == 'manual':
            continue
        items=[]
        for t in row.get('targets') or []:
            key=(t['target_type'], t['value'])
            if key in seen: continue
            seen.add(key); selected.append(t); items.append(t)
            if len(items)>=take: break
        by_segment[seg]=items
    # If a segment is underfilled (e.g. one Winner with budget 10), redistribute
    # remaining capacity to promising/new active targets without duplicates.
    remaining=max(0, limit-len(selected))
    if remaining:
        for seg in ['promising','new','winner']:
            for t in (budget.get('allocation') or []):
                if t.get('segment')!=seg: continue
                for item in t.get('targets') or []:
                    key=(item['target_type'], item['value'])
                    if key in seen: continue
                    seen.add(key); selected.append(item); by_segment.setdefault('redistributed_'+seg,[]).append(item); remaining-=1
                    if remaining<=0: break
                if remaining<=0: break
            if remaining<=0: break
    keywords=[t['value'] for t in selected if t['target_type']=='keyword']
    domains=[t['value'] for t in selected if t['target_type']=='domain']
    return {'budget':budget,'selected':selected,'by_segment':by_segment,'keywords':keywords,'domains':domains}

def _domain_topics(db:Session, domain:str)->list[str]:
    with db.no_autoflush:
        rows=db.query(models.CollectorTarget).filter_by(target_type='domain',value=domain,status='active').order_by(models.CollectorTarget.priority.desc()).limit(5).all()
    topics=[]
    for r in rows:
        for text in [r.topic or '']:
            kw=normalize_keyword(text)
            if kw and kw not in topics: topics.append(kw)
    return topics[:4]

def _collector_target_refs(db:Session, evidence:dict)->list[int]:
    """Resolve candidate evidence back to collector_targets for attribution."""
    refs=[]
    keyword_values=[]
    for k in ['seed','root','topic','query']:
        v=normalize_keyword(str(evidence.get(k) or ''))
        if v: keyword_values.append(v)
    domain_values=[]
    for k in ['source_domain','domain','seed_domain','similar_domain']:
        v=str(evidence.get(k) or '').strip().lower().removeprefix('www.')
        if v: domain_values.append(v)
    with db.no_autoflush:
        for v in keyword_values[:4]:
            rows=db.query(models.CollectorTarget).filter_by(target_type='keyword',value=v).limit(8).all()
            refs.extend([r.id for r in rows])
        for v in domain_values[:4]:
            rows=db.query(models.CollectorTarget).filter_by(target_type='domain',value=v).limit(8).all()
            refs.extend([r.id for r in rows])
    out=[]
    for x in refs:
        if x not in out: out.append(x)
    return out[:12]

def _touch_collector_target_ids(db:Session, target_ids:list[int], success:bool=False, reject:bool=False)->None:
    now=datetime.utcnow()
    for tid in target_ids[:20]:
        t=db.get(models.CollectorTarget, tid)
        if not t: continue
        t.last_seen_at=now
        if success:
            t.success_count=(t.success_count or 0)+1
            t.last_success_at=now
            t.priority=min(100.0, (t.priority or 0)+3.0)
            if t.status=='cooldown': t.status='active'
        if reject:
            t.reject_count=(t.reject_count or 0)+1
        db.merge(t)

def _title_matches_topic(title:str, topic:str)->bool:
    tt=set(normalize_keyword(title).split())
    qt=set(normalize_keyword(topic).split())
    if not tt or not qt: return False
    important={'vendor','compliance','risk','checklist','procurement','security','audit','soc','gdpr','hipaa','tax','invoice'}
    return len(tt & qt) >= 2 or bool((tt & qt) and (tt & important) and (qt & important))

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

def sitemap_url_is_task_page(url:str)->bool:
    """Allow sitemap URL-path extraction only for task/tool-like pages.

    Editorial/blog/resource paths are handled by Domain Web Collector where
    title/meta/h1 can prove tool intent; URL path alone is too noisy.
    """
    path=(urlparse(url).path or '').lower()
    if re.search(r"/(tools?|templates?|calculators?|checklists?|pricing|features|compare|alternatives?|integrations?|apps?)/", path):
        return True
    if re.search(r"\b(calculator|template|checklist|tracker|generator|estimator|automation|dashboard|api|integration|alternative)\b", path):
        return True
    if re.search(r"/(blog|blogs|resources?|articles?|news|guides?)/", path):
        return False
    return False

def keyword_from_title(title:str)->str:
    title=html.unescape(title or '')
    # Remove common brand suffixes: "Keyword - Brand", "Keyword | Brand".
    title=re.split(r"\s+[\-|–|—|•|:]\s+", title, maxsplit=1)[0]
    title=re.sub(r"\b(2024|2025|2026|free|best|top)\b", " ", title, flags=re.I)
    return normalize_keyword(title)

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
    raw=(keyword or '').lower().strip()
    if raw.startswith(('blog ', 'blogs ', 'with ', 'using ')):
        return 'url_path_residue'
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
    if terms[0] in {"blog","blogs","with","using"}: return 'url_path_residue'
    if len(set(terms)) < max(2, len(terms)-1): return 'repeated_terms'
    if any(t in {"crack","apk","coupon","promo"} for t in terms): return 'low_commercial_quality'
    if all(t in NOISE_TERMS for t in terms): return 'generic_noise'
    if re.search(r"\b\d{8,}\b", kw): return 'social_activity_id_noise'
    if len(terms) <= 2 and not any(t in TOOL_INTENT_TERMS for t in terms): return 'generic_short_tail'
    if re.search(r"\bhow to\b", kw) and not any(t in TOOL_INTENT_TERMS for t in terms): return 'tutorial_intent_not_tool'
    if any(t in {"youtube","reddit","github"} for t in terms): return 'platform_title_residue'
    if any(t in {"job","jobs","employment","hiring","freelancer"} for t in terms): return 'jobs_or_hiring_noise'
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
    if source in {'advanced_search','hn_algolia','arxiv','domain_web','alternatives','hot_topic'}:
        if source in {'domain_web','alternatives'} and ({'compliance','tax','invoice','vendor'} & terms and {'checklist','deadline','requirements','cost','roi','automation','calculator','tracker'} & terms):
            return ''
        if not has_tool:
            return 'missing_tool_intent'
        if not has_commercial:
            return 'missing_commercial_modifier'
        root=(evidence or {}).get('root') or (evidence or {}).get('seed') or ''
        root_terms=set(normalize_keyword(root).split()) if root else set()
        if root_terms and not (terms & root_terms):
            return 'root_mismatch'
    if source == 'sitemap':
        # Sitemap paths include many blog/editorial slugs. Keep them only when
        # they look like a concrete task/tool/checklist/compliance deadline.
        if not has_tool and not ({'compliance','tax','invoice'} & terms and {'checklist','deadline','requirements','cost','roi','automation'} & terms):
            return 'sitemap_editorial_path'
    if source == 'short_tail_rewrite':
        if not has_tool or not has_commercial:
            return 'rewrite_missing_commercial_task'
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
        reason=candidate_noise_reason(r.keyword, ev) or candidate_quality_reject_reason(r.keyword, r.source, ev)
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
    roi_verdicts={}
    try:
        roi_verdicts={r['source']:r['verdict'] for r in collector_roi_stats(db, limit=12).get('by_source',[])}
    except Exception:
        roi_verdicts={}
    active=[]; paused=[]; roi_adjustments=[]
    for f in families:
        enabled=(services.setting(db,f['setting']) or 'true').lower() in {'1','true','yes','on'}
        weight=_collector_family_weight(db, f['key'])
        base_weight=weight
        if roi_verdicts.get(f['key'])=='increase':
            weight=round(min(2.5, weight*1.18),3)
            roi_adjustments.append({'source':f['key'],'action':'increase','before':base_weight,'after':weight,'reason':'source ROI verdict=increase'})
        elif roi_verdicts.get(f['key'])=='decrease':
            weight=round(max(0.25, weight*0.75),3)
            roi_adjustments.append({'source':f['key'],'action':'decrease','before':base_weight,'after':weight,'reason':'source ROI verdict=decrease'})
        row={**f,'enabled':enabled,'weight':weight}
        if roi_verdicts.get(f['key']): row['roi_verdict']=roi_verdicts.get(f['key'])
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
    return {'limit':limit,'min_weight':min_weight,'active':active,'paused':paused,'weights':_collector_source_weights(db),'roi_adjustments':roi_adjustments}

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
    evidence.setdefault('collector_target_ids', _collector_target_refs(db, evidence))
    reason=candidate_noise_reason(kw, evidence) or candidate_quality_reject_reason(kw, source, evidence)
    source_url = source_url or ''
    for obj in list(db.new):
        if isinstance(obj, models.CandidateKeyword) and obj.keyword == kw and obj.source == source and (obj.source_url or '') == source_url:
            return None
    if reason:
        if reason == 'generic_short_tail':
            rewrites=[]
            for variant in expand_generic_short_tail(kw):
                rewrites.append(variant)
                # Add rewritten task variants as importable candidates while
                # preserving the original short-head as rejected evidence.
                upsert_candidate(db, variant, 'short_tail_rewrite', source_url, source_domain, '短头词改写', {**evidence, 'original_keyword': kw, 'rewrite_reason': reason}, max(score, 0.57))
            evidence['rewrite_candidates']=rewrites
        # Store rejected evidence for observability, but never let obvious source
        # noise enter the importable candidate pool.
        with db.no_autoflush:
            q=db.query(models.CandidateKeyword).filter_by(keyword=kw, source=source, source_url=source_url).first()
        ev={**evidence, 'reject_reason': reason, 'canonical_keyword': canonical_keyword(kw)}
        if q:
            q.status='rejected'; q.evidence_json=json.dumps({**(json.loads(q.evidence_json or '{}') if q.evidence_json else {}), **ev}, ensure_ascii=False); db.merge(q); return None
        row=models.CandidateKeyword(keyword=kw, source=source, source_url=source_url, source_domain=source_domain or '', method=method, evidence_json=json.dumps(ev, ensure_ascii=False), score=0.0, status='rejected')
        db.add(row); return None
    computed_score=round(max(0.0, min(1.0, score_candidate(kw, source, evidence, score) * collector_source_multiplier(db, source))), 3)
    with db.no_autoflush:
        q=db.query(models.CandidateKeyword).filter_by(keyword=kw, source=source, source_url=source_url).first()
    if q:
        if q.status != 'new':
            old_status=q.status
            q.status='new'
            q.score=max(q.score or 0, computed_score)
            q.evidence_json=json.dumps({**(json.loads(q.evidence_json or '{}') if q.evidence_json else {}), **(evidence or {}), 'resurrected_from': old_status}, ensure_ascii=False)
            db.merge(q); return q
        q.score=max(q.score, computed_score)
        q.evidence_json=json.dumps({**(json.loads(q.evidence_json or '{}') if q.evidence_json else {}), **(evidence or {})}, ensure_ascii=False)
        db.merge(q); return q
    row=models.CandidateKeyword(keyword=kw, source=source, source_url=source_url, source_domain=source_domain or '', method=method, evidence_json=json.dumps(evidence or {}, ensure_ascii=False), score=computed_score, status='new')
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
    total=0; imported=0; new_urls=0; old_urls=0; skipped_editorial=0; errors=[]
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
                if not sitemap_url_is_task_page(url):
                    skipped_editorial+=1
                    continue
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
    return {'ok':True,'source':'sitemap','domains':len(domains),'urls_seen':total,'new_urls':new_urls,'old_urls':old_urls,'skipped_editorial':skipped_editorial,'saved':imported,'only_new':only_new,'errors':errors[:20]}

def _fetch_html(url:str, timeout:float=8)->str:
    r=requests.get(url, headers={'User-Agent':'Mozilla/5.0 (DemandHunterBot/1.0)'}, timeout=timeout)
    r.raise_for_status()
    ctype=(r.headers.get('content-type') or '').lower()
    if 'text/html' not in ctype and 'application/xhtml' not in ctype and not url.endswith('/'):
        return ''
    return r.text[:250000]

def extract_page_keywords(url:str)->list[dict]:
    """Fetch one public HTML page and extract title/meta/h1-derived keywords."""
    try:
        text=_fetch_html(url)
    except Exception:
        return []
    if not text: return []
    snippets=[]
    title_m=re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I|re.S)
    if title_m: snippets.append(('title', re.sub(r"\s+", " ", title_m.group(1))))
    for m in re.finditer(r"<meta[^>]+(?:name|property)=['\"](?:description|og:title|twitter:title)['\"][^>]+content=['\"]([^'\"]+)['\"]", text, flags=re.I):
        snippets.append(('meta', m.group(1)))
    for m in re.finditer(r"<h1[^>]*>(.*?)</h1>", text, flags=re.I|re.S):
        snippets.append(('h1', re.sub(r"<[^>]+>", " ", m.group(1))))
    out=[]; seen=set()
    for kind,s in snippets[:8]:
        kw=keyword_from_title(s)
        if kw and kw not in seen:
            seen.add(kw); out.append({'keyword':kw,'kind':kind,'text':html.unescape(re.sub(r"\s+", " ", s)).strip()[:300]})
    return out

def run_domain_web_collector(db:Session, domains:list[str], max_pages_per_domain:int=8, max_seconds:int|None=None)->dict:
    """Free web-page collector: sitemap URLs -> title/meta/h1 keywords.

    This simulates manual competitor-page research without paid SEO APIs.
    """
    try: max_seconds=int(max_seconds if max_seconds is not None else (services.setting(db,'COLLECTOR_DOMAIN_WEB_MAX_SECONDS') or '35'))
    except Exception: max_seconds=35
    started=time.monotonic(); seen=0; saved=0; errors=[]
    path_hints=re.compile(r"/(tools?|templates?|calculators?|checklists?|pricing|features|compare|alternatives?|integrations?)/", re.I)
    editorial_tool_hints=re.compile(r"/(blog|blogs|resources?|articles?|guides?)/.*\b(calculator|template|checklist|tracker|generator|automation|dashboard|api|integration|alternative)\b", re.I)
    for d in domains:
        _touch_collector_target(db,'domain',d)
        if time.monotonic()-started>max_seconds:
            errors.append({'domain':d,'error':f'time_budget_exceeded>{max_seconds}s'}); break
        try:
            urls=[]
            queue=discover_sitemaps(d)
            while queue and len(urls)<max_pages_per_domain*4 and time.monotonic()-started<=max_seconds:
                sm=queue.pop(0)
                try:
                    pages, childs=parse_sitemap_urls(sm, max_urls=max_pages_per_domain*4-len(urls))
                    urls.extend([u for u in pages if path_hints.search(urlparse(u).path or '') or editorial_tool_hints.search(urlparse(u).path or '')])
                    queue.extend(childs[:5])
                except Exception:
                    continue
            if not urls:
                root=d if d.startswith('http') else 'https://'+d
                urls=[root.rstrip('/')+'/']
            for url in urls[:max_pages_per_domain]:
                if time.monotonic()-started>max_seconds: break
                for item in extract_page_keywords(url):
                    seen+=1
                    evidence={'url':url,'title':item['text'],'extractor':item['kind'],'domain':domain_of(url)}
                    row=upsert_candidate(db, item['keyword'], 'domain_web', url, domain_of(url), '页面标题/Meta 找词', evidence, 0.62)
                    if row:
                        saved+=1
                        _touch_collector_target(db,'domain',d,success=True)
        except Exception as e:
            errors.append({'domain':d,'error':str(e)[:180]})
    db.commit()
    return {'ok':True,'source':'domain_web','domains':len(domains),'pages_seen':seen,'saved':saved,'errors':errors[:20]}

def run_alternatives_collector(db:Session, domains:list[str], max_seconds:int|None=None)->dict:
    """Find similar/alternative domains through public search queries."""
    try: max_seconds=int(max_seconds if max_seconds is not None else (services.setting(db,'COLLECTOR_ALTERNATIVES_MAX_SECONDS') or '35'))
    except Exception: max_seconds=35
    started=time.monotonic(); seen=0; saved=0; errors=[]
    providers=services.available_serp_providers(db)
    for d in domains[:12]:
        _touch_collector_target(db,'domain',d)
        if time.monotonic()-started>max_seconds:
            errors.append({'domain':d,'error':f'time_budget_exceeded>{max_seconds}s'}); break
        brand=d.split('.')[0]
        topics=_domain_topics(db,d)
        topic_queries=[]
        for topic in topics[:3]:
            topic_queries.extend([f'{topic} alternatives', f'best {topic} tools', f'{topic} software comparison', f'{brand} alternative {topic}'])
        queries=(topic_queries or [f'{brand} alternatives software', f'{brand} vs competitors', f'best {brand} alternatives software'])[:8]
        for q in queries:
            if time.monotonic()-started>max_seconds: break
            items=[]; provider_used=''
            for p in providers[:2]:
                try:
                    provider_used=p; res=services.provider_search(db,p,q,limit=5)
                    if res and res[0].get('engine')!='error': items=res; break
                except Exception as e:
                    errors.append({'query':q,'provider':p,'error':str(e)[:160]})
            for item in items[:5]:
                url=item.get('url') or item.get('link') or ''
                cd=domain_of(url)
                if not cd or is_blocked_domain(cd) or cd==d: continue
                seen+=1
                title=item.get('title') or ''
                kw=keyword_from_title(title) or normalize_keyword(f'{brand} alternatives')
                # Avoid dictionary/app-store false positives from bare brand searches.
                if is_blocked_domain(cd) or re.search(r"\b(definition|meaning|download|hotel|video downloader)\b", (title or '').lower()):
                    _touch_collector_target(db,'domain',d,reject=True)
                    continue
                if topics and not any(_title_matches_topic(title, topic) for topic in topics):
                    _touch_collector_target(db,'domain',d,reject=True)
                    continue
                evidence={'query':q,'title':title,'url':url,'provider':provider_used,'seed_domain':d,'similar_domain':cd}
                row=upsert_candidate(db, kw, 'alternatives', url, cd, '站找站', evidence, 0.60)
                if row:
                    saved+=1
                    _touch_collector_target(db,'domain',d,success=True)
                    _upsert_collector_target(db,'domain',cd,'alternative_to',d,_target_topic(kw),70.0,f'alternative search from {d}: {title[:120]}')
    db.commit()
    return {'ok':True,'source':'alternatives','domains':len(domains),'seen':seen,'saved':saved,'errors':errors[:20]}

def run_hot_topic_collector(db:Session, topics:list[str]|None=None, max_seconds:int|None=None)->dict:
    """Lightweight hot-topic collector from active target topics.

    Uses public SERP providers with freshness/modifier queries instead of paid
    trends APIs. Candidates still go through normal quality gates.
    """
    try: max_seconds=int(max_seconds if max_seconds is not None else (services.setting(db,'COLLECTOR_HOT_TOPIC_MAX_SECONDS') or '35'))
    except Exception: max_seconds=35
    if not topics:
        rows=db.query(models.CollectorTarget).filter_by(status='active').order_by(models.CollectorTarget.priority.desc()).limit(40).all()
        topics=[]
        for r in rows:
            topic=normalize_keyword(r.topic or r.value or '')
            if topic and topic not in topics: topics.append(topic)
    topics=[t for t in topics if t][:12]
    providers=services.available_serp_providers(db)
    started=time.monotonic(); seen=0; saved=0; errors=[]
    modifiers=['2026','deadline','new regulation','ai tool','template','calculator','checklist','automation']
    for topic in topics:
        _touch_collector_target(db,'keyword',topic)
        if time.monotonic()-started>max_seconds:
            errors.append({'topic':topic,'error':f'time_budget_exceeded>{max_seconds}s'}); break
        for mod in modifiers[:4]:
            if time.monotonic()-started>max_seconds: break
            q=f'{topic} {mod}'
            items=[]; provider_used=''
            for p in providers[:2]:
                try:
                    provider_used=p; res=services.provider_search(db,p,q,limit=5)
                    if res and res[0].get('engine')!='error': items=res; break
                except Exception as e:
                    errors.append({'query':q,'provider':p,'error':str(e)[:160]})
            for item in items[:5]:
                title=item.get('title') or ''
                url=item.get('url') or item.get('link') or ''
                d=domain_of(url)
                if not d or is_blocked_domain(d): continue
                if not _title_matches_topic(title, topic): continue
                kw=keyword_from_title(title) or normalize_keyword(q)
                evidence={'query':q,'topic':topic,'modifier':mod,'title':title,'url':url,'provider':provider_used}
                row=upsert_candidate(db, kw, 'hot_topic', url, d, '热点词/新鲜度找词', evidence, 0.61)
                seen+=1
                if row:
                    saved+=1
                    _touch_collector_target(db,'keyword',topic,success=True)
    db.commit()
    return {'ok':True,'source':'hot_topic','topics':len(topics),'seen':seen,'saved':saved,'errors':errors[:20]}

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
        _touch_collector_target(db,'keyword',seed)
        if time.monotonic() - started > max_seconds:
            errors.append({'seed':seed,'error':f'time_budget_exceeded>{max_seconds}s'})
            break
        for item in suggest_queries(seed, timeout=4):
            seen+=1
            row=upsert_candidate(db, item['keyword'], item['source'], '', '', '词找词', {'seed':seed,'provider':item['source']}, 0.55)
            if row:
                saved+=1
                _touch_collector_target(db,'keyword',seed,success=True)
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
        if not ev.get('collector_target_ids'):
            ev['collector_target_ids']=_collector_target_refs(db, {**ev, 'source_domain': c.source_domain, 'query': ev.get('query') or c.keyword})
        existing=db.query(models.Keyword).filter_by(query=query).first()
        if not existing:
            root_meta={'candidate_id':c.id,'candidate_source':c.source,'collector_target_ids':ev.get('collector_target_ids') or [],'source_url':c.source_url,'source_domain':c.source_domain}
            db.add(models.Keyword(query=query, source=f'collector:{c.source}', root_terms=json.dumps(root_meta, ensure_ascii=False), score=c.score, status='new'))
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
    target_ids=[]
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
        if not ev.get('collector_target_ids'):
            ev['collector_target_ids']=_collector_target_refs(db, {**ev, 'source_domain': cand.source_domain, 'query': ev.get('query') or cand.keyword})
        for tid in ev.get('collector_target_ids') or []:
            if tid not in target_ids: target_ids.append(tid)
        cand.evidence_json=json.dumps(ev, ensure_ascii=False)
        db.merge(cand)

    # If the candidate evidence was not found (old imported keyword), fall back
    # to root_terms metadata written during import.
    if not target_ids:
        try:
            meta=json.loads(keyword.root_terms or '{}')
            for tid in meta.get('collector_target_ids') or []:
                if tid not in target_ids: target_ids.append(tid)
        except Exception:
            pass
    if target_ids:
        _touch_collector_target_ids(db, target_ids, success=good, reject=bad)
    affected_targets=[]
    for tid in target_ids[:12]:
        t=db.get(models.CollectorTarget, tid)
        if t:
            affected_targets.append({'id':t.id,'type':t.target_type,'value':t.value,'status':t.status,'priority':t.priority,'success_count':t.success_count,'reject_count':t.reject_count})

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
    return {'applied':True,'source':source,'label':label,'matched_candidates':len(matched),'source_weight':weights[source]['weight'],'seed_count':len(seeds),'domain_count':len(auto_domains),'affected_targets':affected_targets,'target_effect':'reward' if good else 'penalty'}

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
    target_refresh = refresh_collector_targets_from_cards(db)
    budgeted_targets=select_budgeted_collector_targets(db, limit=max(4,limit))
    target_keywords=budgeted_targets['keywords']
    target_domains=budgeted_targets['domains']
    manual_seeds=_split_setting_list(services.setting(db,'COLLECTOR_AUTO_SEEDS'))
    manual_domains=_split_setting_list(services.setting(db,'COLLECTOR_AUTO_DOMAINS'))
    seeds=[]
    for s in target_keywords + manual_seeds:
        if s and s not in seeds: seeds.append(s)
    domains=[]
    for d in target_domains + manual_domains:
        if d and d not in domains: domains.append(d)
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
        print(f"[collector] starting suggest, {len(seeds[:active['suggest']['item_limit']])} seeds, budget_left={max_seconds - (time.monotonic()-started):.0f}s", flush=True)
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_suggest_collector(db, seeds[:active['suggest']['item_limit']], max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_SUGGEST_MAX_SECONDS') or '20'))))
        except Exception as e: errors.append({'collector':'suggest','error':str(e)[:180]})
        print(f"[collector] suggest done, elapsed={time.monotonic()-started:.1f}s", flush=True)
    if domains and 'sitemap' in active and budget_left():
        try: results.append(run_sitemap_watcher(db, domains[:active['sitemap']['item_limit']], max_urls_per_domain=active['sitemap'].get('max_urls_per_domain', max(20,min(120,limit*4))), only_new=True))
        except Exception as e: errors.append({'collector':'sitemap','error':str(e)[:180]})
    if domains and budget_left() and (services.setting(db,'COLLECTOR_DOMAIN_WEB_ENABLED') or 'true').lower() in {'1','true','yes','on'}:
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_domain_web_collector(db, domains[:max(2, min(8, limit//2))], max_pages_per_domain=4, max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_DOMAIN_WEB_MAX_SECONDS') or '25'))))
        except Exception as e: errors.append({'collector':'domain_web','error':str(e)[:180]})
    if domains and budget_left() and (services.setting(db,'COLLECTOR_ALTERNATIVES_ENABLED') or 'true').lower() in {'1','true','yes','on'}:
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_alternatives_collector(db, domains[:max(2, min(6, limit//3))], max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_ALTERNATIVES_MAX_SECONDS') or '25'))))
        except Exception as e: errors.append({'collector':'alternatives','error':str(e)[:180]})
    if seeds and 'advanced_search' in active and budget_left():
        roots=seeds[:active['advanced_search']['item_limit']]
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        print(f"[collector] starting advanced_search, {len(roots)} roots, budget_left={remaining}s", flush=True)
        try: results.append(run_advanced_search_collector(db, roots, domains[:6], days=45, limit_per_query=active['advanced_search'].get('limit_per_query',5), max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_ADVANCED_MAX_SECONDS') or '90'))))
        except Exception as e: errors.append({'collector':'advanced_search','error':str(e)[:180]})
        print(f"[collector] advanced_search done, elapsed={time.monotonic()-started:.1f}s", flush=True)
    if seeds and budget_left() and (services.setting(db,'COLLECTOR_HOT_TOPIC_ENABLED') or 'true').lower() in {'1','true','yes','on'}:
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        try: results.append(run_hot_topic_collector(db, topics=seeds[:max(2,min(6,limit//2))], max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_HOT_TOPIC_MAX_SECONDS') or '20'))))
        except Exception as e: errors.append({'collector':'hot_topic','error':str(e)[:180]})
    if seeds and 'source_radar' in active and budget_left():
        remaining=max(5, int(max_seconds - (time.monotonic() - started)))
        print(f"[collector] starting source_radar, budget_left={remaining}s", flush=True)
        try: results.append(run_source_radar(db, seeds[:active['source_radar']['item_limit']], limit_per_seed=active['source_radar'].get('limit_per_seed',6), max_seconds=min(remaining, int(services.setting(db,'COLLECTOR_SOURCE_RADAR_MAX_SECONDS') or '45'))))
        except Exception as e: errors.append({'collector':'source_radar','error':str(e)[:180]})
        print(f"[collector] source_radar done, elapsed={time.monotonic()-started:.1f}s", flush=True)
    if not budget_left():
        errors.append({'collector':'autopilot','error':f'time_budget_exceeded>{max_seconds}s'})
    clean=clean_candidate_pool(db, limit=max(200, limit*10))
    imported=import_candidates_to_keywords(db, limit=max(1, import_limit))
    target_health=apply_collector_target_health(db)
    payload={'enabled':True,'target_refresh':target_refresh,'target_health':target_health,'budgeted_targets':{'allocation':budgeted_targets['budget'].get('allocation'),'by_segment':budgeted_targets['by_segment']},'seeds':seeds,'domains':domains,'auto_targets':{'keywords':target_keywords[:20],'domains':target_domains[:20]},'budget_plan':plan,'results':results,'errors':errors[:20],'clean':clean,'import':imported,'summary':collector_pool_summary(db)}
    # Persist a compact replay record so the operator can compare budget vs.
    # actual results across runs.
    try:
        replay={
            'limit': limit,
            'import_limit': import_limit,
            'selected_by_segment': {k:[{'id':t.get('id'),'type':t.get('target_type'),'value':t.get('value'),'priority':t.get('priority'),'success':t.get('success_count'),'reject':t.get('reject_count')} for t in v[:20]] for k,v in budgeted_targets['by_segment'].items()},
            'source_results': [{'source':r.get('source'),'saved':r.get('saved'),'seen':r.get('candidates_seen') or r.get('seen') or r.get('urls_seen') or r.get('pages_seen'),'errors':len(r.get('errors') or [])} for r in results if isinstance(r,dict)],
            'clean': clean,
            'import': imported,
            'target_health': target_health,
            'errors': errors[:10],
        }
        db.add(models.RunHistory(kind='collector_autopilot', status='ok', summary=json.dumps(replay, ensure_ascii=False), finished_at=datetime.utcnow()))
        db.commit()
    except Exception:
        db.rollback()
    return payload

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
    empty_streak: dict[str,int] = {p: 0 for p in providers}
    for q,root,variant in queries[:80]:
        _touch_collector_target(db,'keyword',root)
        if time.monotonic() - started > max_seconds:
            errors.append({'query':q,'error':f'time_budget_exceeded>{max_seconds}s'})
            break
        provider_used=''
        items=[]
        for p in providers[:max(1, int(services.setting(db,'SERP_PROVIDER_ATTEMPT_LIMIT') or '3'))]:
            if time.monotonic() - started > max_seconds:
                break
            if empty_streak.get(p, 0) >= 3:
                continue  # skip provider that returned 0 results 3 times in a row
            provider_used=p
            try:
                res=services.provider_search(db,p,q,limit=limit_per_query)
            except Exception as e:
                errors.append({'query':q,'provider':p,'error':str(e)[:180]})
                empty_streak[p] = empty_streak.get(p, 0) + 1
                continue
            print(f"[advanced] query={q[:60]} provider={provider_used} items={len(res or [])} elapsed={time.monotonic()-started:.1f}s", flush=True)
            if res and res[0].get('engine')!='error':
                items=res; break
            else:
                empty_streak[p] = empty_streak.get(p, 0) + 1
        else:
            # reset streak on success
            if provider_used and items:
                empty_streak[provider_used] = 0
        if not items:
            errors.append({'query':q,'error':'no results'})
            continue
        for item in items:
            kw=_candidate_from_search_result(item)
            if not kw: continue
            seen+=1
            url=item.get('url') or item.get('link') or ''
            row=upsert_candidate(db, kw, 'advanced_search', url, domain_of(url), '高级搜索找需求', {'query':q,'root':root,'variant':variant,'provider':provider_used,'title':item.get('title',''),'url':url}, 0.58)
            if row:
                saved+=1
                _touch_collector_target(db,'keyword',root,success=True)
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
    tech_only=(services.setting(db,'COLLECTOR_SOURCE_RADAR_TECH_ONLY') or 'true').lower() in {'1','true','yes','on'}
    for seed in [s.strip() for s in seeds if s.strip()]:
        if tech_only and not (set(normalize_keyword(seed).split()) & TECH_SOURCE_RADAR_TERMS):
            errors.append({'source':'source_radar','seed':seed,'error':'skipped_non_tech_seed'})
            continue
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
