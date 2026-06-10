from __future__ import annotations
from datetime import datetime
from pathlib import Path
import hashlib, json, re, requests
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app import models, services
from app.database import engine

ROOT = Path(__file__).resolve().parents[2]
PRD_ROOT = ROOT / "prds"

def ensure_tables():
    for cls in [models.MvpProject, models.MvpValidationRun, models.TrackedCompetitor, models.CompetitorSnapshot, models.MvpStrategyRecommendation, models.ProgressHypothesis, models.ProgressEvidenceTask, models.ProgressEvidenceItem]:
        cls.__table__.create(bind=engine, checkfirst=True)
    # Lightweight SQLite-compatible column migration for iterative progress tables.
    try:
        with engine.begin() as conn:
            cols=[r[1] for r in conn.exec_driver_sql('PRAGMA table_info(progress_evidence_items)').fetchall()]
            if 'reason' not in cols:
                conn.exec_driver_sql('ALTER TABLE progress_evidence_items ADD COLUMN reason TEXT DEFAULT ""')
    except Exception:
        pass

def slugify(s:str)->str:
    return re.sub(r"[^a-z0-9]+","-",(s or "project").lower()).strip("-")[:80] or "project"

def _card_obj(db:Session, card:models.OpportunityCard):
    kw=db.get(models.Keyword, card.keyword_id)
    group=services.opportunity_group_for_card(db, card)
    return {"card_id":card.id,"keyword":kw.query if kw else card.title,"verdict":card.verdict,"feedback_label":card.feedback_label,"score":card.score,"group":group}

def _json_loads(s, default):
    try: return json.loads(s or "")
    except Exception: return default

def _short(s:str, n:int=12000)->str:
    s=s or ""
    return s if len(s)<=n else s[:n] + f"\n\n[TRUNCATED_FOR_ANALYSIS original_chars={len(s)}]"

def _card_detail(db:Session, card:models.OpportunityCard|None):
    if not card: return None
    kw=db.get(models.Keyword, card.keyword_id)
    evidence=_json_loads(card.evidence_json, [])
    risks=_json_loads(card.risks, [])
    business=next((e for e in evidence if isinstance(e,dict) and e.get("type")=="business"), {})
    group=services.opportunity_group_for_card(db, card)
    return {
        "id": card.id,
        "title": card.title,
        "keyword": kw.query if kw else card.title,
        "keyword_source": kw.source if kw else "",
        "verdict": card.feedback_label or card.verdict,
        "model_verdict": card.verdict,
        "score": card.score,
        "demand_score": card.demand_score,
        "serp_gap_score": card.serp_gap_score,
        "competitor_weakness_score": card.competitor_weakness_score,
        "commercial_score": card.mvp_score,
        "monetization_score": card.monetization_score,
        "monetization_type": card.monetization_type,
        "mvp_plan": card.mvp_plan,
        "risks": risks,
        "business": business,
        "evidence": evidence[:24] if isinstance(evidence,list) else [],
        "opportunity_group": group,
    }

def list_projects(db:Session):
    ensure_tables()
    rows=db.query(models.MvpProject).order_by(models.MvpProject.updated_at.desc()).all()
    out=[]
    for p in rows:
        card=db.get(models.OpportunityCard,p.representative_card_id) if p.representative_card_id else None
        original=float(card.score or 0) if card else 0.0
        display_score=float(p.feasibility_score or original or 0)
        out.append({"id":p.id,"opportunity_group_id":p.opportunity_group_id,"canonical_keyword":p.canonical_keyword,"representative_card_id":p.representative_card_id,"status":p.status,"prd_version":p.prd_version,"feasibility_score":display_score,"original_score":original,"score_delta":round(display_score-original,1) if p.last_validated_at else 0,"risk_level":p.risk_level,"next_action":p.next_action,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat(),"last_validated_at":p.last_validated_at.isoformat() if p.last_validated_at else None,"opportunity":_card_detail(db,card)})
    return out

def get_project(db:Session, project_id:int):
    ensure_tables()
    p=db.get(models.MvpProject, project_id)
    if not p: return None
    card=db.get(models.OpportunityCard,p.representative_card_id) if p.representative_card_id else None
    runs=db.query(models.MvpValidationRun).filter_by(project_id=p.id).order_by(models.MvpValidationRun.started_at.desc()).limit(20).all()
    competitors=db.query(models.TrackedCompetitor).filter_by(project_id=p.id).order_by(models.TrackedCompetitor.created_at.desc()).all()
    recs=db.query(models.MvpStrategyRecommendation).filter_by(project_id=p.id).order_by(models.MvpStrategyRecommendation.created_at.desc()).all()
    hyps=db.query(models.ProgressHypothesis).filter_by(project_id=p.id).order_by(models.ProgressHypothesis.created_at.asc()).all()
    tasks=db.query(models.ProgressEvidenceTask).filter_by(project_id=p.id).order_by(models.ProgressEvidenceTask.created_at.asc()).all()
    evidence=db.query(models.ProgressEvidenceItem).filter_by(project_id=p.id).order_by(models.ProgressEvidenceItem.captured_at.desc()).limit(80).all()
    original=float(card.score or 0) if card else 0.0
    display_score=float(p.feasibility_score or original or 0)
    return {"project":list_projects(db=[].__class__) if False else {"id":p.id,"opportunity_group_id":p.opportunity_group_id,"canonical_keyword":p.canonical_keyword,"representative_card_id":p.representative_card_id,"status":p.status,"prd_path":p.prd_path,"prd_version":p.prd_version,"prd_content":p.prd_content,"feasibility_score":display_score,"original_score":original,"score_delta":round(display_score-original,1) if p.last_validated_at else 0,"risk_level":p.risk_level,"next_action":p.next_action,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat(),"last_validated_at":p.last_validated_at.isoformat() if p.last_validated_at else None,"opportunity":_card_detail(db,card)},"runs":[{"id":r.id,"kind":r.kind,"status":r.status,"summary":json.loads(r.summary_json or "{}"),"score_delta":r.score_delta,"started_at":r.started_at.isoformat(),"finished_at":r.finished_at.isoformat() if r.finished_at else None} for r in runs],"competitors":[{"id":c.id,"domain":c.domain,"name":c.name,"url":c.url,"pricing_url":c.pricing_url,"sitemap_url":c.sitemap_url,"status":c.status,"notes":c.notes,"last_seen_at":c.last_seen_at.isoformat() if c.last_seen_at else None} for c in competitors],"recommendations":[{"id":r.id,"type":r.type,"title":r.title,"content":r.content,"confidence":r.confidence,"status":r.status,"created_at":r.created_at.isoformat()} for r in recs],"hypotheses":[{"id":h.id,"title":h.title,"description":h.description,"status":h.status,"confidence":h.confidence,"evidence_count":h.evidence_count,"last_checked_at":h.last_checked_at.isoformat() if h.last_checked_at else None,"next_check_at":h.next_check_at.isoformat() if h.next_check_at else None} for h in hyps],"evidence_tasks":[{"id":t.id,"hypothesis_id":t.hypothesis_id,"query":t.query,"task_type":t.task_type,"status":t.status,"priority":t.priority,"result_summary":t.result_summary,"last_run_at":t.last_run_at.isoformat() if t.last_run_at else None,"next_run_at":t.next_run_at.isoformat() if t.next_run_at else None} for t in tasks],"evidence_items":[{"id":e.id,"hypothesis_id":e.hypothesis_id,"task_id":e.task_id,"title":e.title,"url":e.url,"source_domain":e.source_domain,"snippet":e.snippet,"effect":e.effect,"reason":getattr(e,'reason',''),"confidence":e.confidence,"captured_at":e.captured_at.isoformat()} for e in evidence]}

def create_project_from_card(db:Session, card_id:int):
    ensure_tables()
    card=db.get(models.OpportunityCard, card_id)
    if not card: raise ValueError("card_not_found")
    final=card.feedback_label or card.verdict
    if final != "Adopted": raise ValueError("only_adopted_opportunities_can_start_progress")
    group=services.opportunity_group_for_card(db, card)
    gid=group.get("group_id") or f"card-{card.id}"
    existing=db.query(models.MvpProject).filter_by(opportunity_group_id=gid).first()
    if existing: return existing
    p=models.MvpProject(opportunity_group_id=gid, canonical_keyword=group.get("canonical_keyword") or card.title, representative_card_id=card.id, status="needs_prd", feasibility_score=float(card.score or 0), risk_level="unknown", next_action="上传 PRD.md 后开始产品分析：先判断 PRD 合理性，再验证目标用户、商业逻辑、付费路径、竞品、获客方式并重新评分。")
    db.add(p); db.commit(); db.refresh(p); return p

def save_prd(db:Session, project_id:int, content:str):
    ensure_tables()
    p=db.get(models.MvpProject, project_id)
    if not p: raise ValueError("project_not_found")
    content=(content or "").strip()
    if not content: raise ValueError("prd_empty")
    slug=slugify(p.canonical_keyword)
    folder=PRD_ROOT/slug; folder.mkdir(parents=True, exist_ok=True)
    path=folder/"PRD.md"
    path.write_text(content, encoding="utf-8")
    p.prd_content=content; p.prd_path=str(path.relative_to(ROOT)); p.prd_version=(p.prd_version or 0)+1; p.status="prd_ready"; p.next_action="PRD 已保存，准备启动产品分析。"
    db.merge(p); db.commit(); db.refresh(p); return p

def _domain(url:str)->str:
    try: return urlparse(url).netloc.replace("www.","")
    except Exception: return ""

def _prd_competitor_queries(db:Session, project:models.MvpProject, slim_card:dict):
    text=((project.prd_content or "")+" "+project.canonical_keyword).lower()
    queries=[]
    # Deterministic PRD-shape competitor discovery: understand product shape, not just original keyword.
    if "soc 2" in text or "soc2" in text:
        queries += ["SOC 2 readiness assessment software", "SOC 2 compliance questionnaire tool"]
    if any(x in text for x in ["embed","embedded","嵌入","white label","white-label","白标"]):
        queries += ["white label compliance assessment tool", "embedded assessment tool for consultants"]
    if any(x in text for x in ["lead","线索","sales brief","crm","服务商","consultant","msp","vciso"]):
        queries += ["compliance lead generation tool", "vCISO assessment tool for lead generation"]
    if any(x in text for x in ["calculator","计算器","cost","成本"]):
        queries += ["SOC 2 cost calculator", "compliance cost calculator software"]
    if not queries:
        queries=[project.canonical_keyword, f"{project.canonical_keyword} alternatives", f"{project.canonical_keyword} competitors"]
    out=[]
    for q in queries:
        if q not in out: out.append(q)
    return out[:2]

def _extract_competitors_from_serp(db:Session, project:models.MvpProject, queries:list[str]):
    out=[]; seen=set()
    for q in queries[:2]:
        try:
            items=services.searxng_search(db, q, limit=3)
            for item in items[:3]:
                url=item.get("url") or item.get("link") or ""
                d=_domain(url)
                if not d or d in seen or d.endswith(".gov"): continue
                seen.add(d)
                title=(item.get("title") or d)[:250]
                c=db.query(models.TrackedCompetitor).filter_by(project_id=project.id, domain=d).first()
                if not c:
                    c=models.TrackedCompetitor(project_id=project.id,domain=d,name=title,url=url,pricing_url="",sitemap_url=f"https://{d}/sitemap.xml",notes=f"来自PRD竞品搜索：{q}",last_seen_at=datetime.utcnow())
                    db.add(c); db.commit(); db.refresh(c)
                out.append(c)
        except Exception:
            db.rollback()
    return out

def _sitemap_probe(db:Session, competitors:list[models.TrackedCompetitor]):
    snapshots=[]
    for c in competitors[:12]:
        try:
            r=requests.get(c.sitemap_url or f"https://{c.domain}/sitemap.xml", timeout=8, headers={"User-Agent":"DemandHunter/1.0"})
            text=r.text[:100000] if r.ok else ""
            urls=re.findall(r"<loc>(.*?)</loc>", text)[:60]
            interesting=[u for u in urls if any(x in u.lower() for x in ["pricing","template","calculator","tool","docs","blog","integration","alternative"])]
            h=hashlib.sha1("\n".join(urls).encode()).hexdigest() if urls else ""
            snap=models.CompetitorSnapshot(competitor_id=c.id,snapshot_type="sitemap",url=c.sitemap_url,title=f"{c.domain} sitemap",content_hash=h,summary_json=json.dumps({"ok":r.ok,"url_count":len(urls),"interesting":interesting[:20]},ensure_ascii=False))
            db.add(snap); c.last_seen_at=datetime.utcnow(); db.merge(c); db.commit(); snapshots.append(snap)
        except Exception as e:
            db.rollback()
    return snapshots

def _seed_progress_loop(db:Session, p:models.MvpProject, analysis:dict, queries:list[str]):
    existing=db.query(models.ProgressHypothesis).filter_by(project_id=p.id).count()
    if existing:
        return
    base=[]
    for item in (analysis.get('evidence_plan') or [])[:6]:
        title=item.get('hypothesis') or item.get('area') or '' if isinstance(item,dict) else str(item)
        if title: base.append((title, item.get('current_evidence','') if isinstance(item,dict) else '', item.get('priority','medium') if isinstance(item,dict) else 'medium'))
    if not base:
        base=[('服务商愿意在官网嵌入评估工具','验证嵌入式问答/assessment 是否是服务商真实采用的获客路径','high'),('服务商愿意为白标 lead capture 工具付费','验证第三方 white-label assessment 工具和价格锚点','high'),('通用 quiz/form 工具不足以满足 SOC 2 销售上下文','验证 Typeform/LeadQuizzes/Outgrow 等替代方案缺口','medium'),('SOC 2 服务商需要带销售上下文的报告和线索','验证 sales brief / CRM-ready fields 是否能提高跟进效率','high')]
    for title,desc,priority in base[:8]:
        h=models.ProgressHypothesis(project_id=p.id,title=title,description=desc,status='unverified',confidence=0.25)
        db.add(h); db.commit(); db.refresh(h)
        task_queries=[]
        low=(title+' '+desc).lower()
        if '嵌入' in title or 'embed' in low or '官网' in title:
            task_queries=['SOC 2 consultant embedded assessment','SOC 2 readiness quiz consultant website']
        elif '白标' in title or 'white' in low:
            task_queries=['white label assessment platform for consultants','white label compliance assessment software']
        elif 'quiz' in low or 'form' in low or '替代' in title:
            task_queries=['LeadQuizzes pricing CRM lead scoring','Outgrow calculator lead generation pricing']
        else:
            task_queries=queries[:2]
        for q in task_queries[:2]:
            db.add(models.ProgressEvidenceTask(project_id=p.id,hypothesis_id=h.id,query=q[:300],task_type='web_search',status='pending',priority=priority or 'medium'))
    db.commit()

def _classify_evidence(db:Session, hypothesis:models.ProgressHypothesis|None, task:models.ProgressEvidenceTask, items:list[dict]):
    if not items or not hypothesis:
        return []
    system="""你是机会验证分析员。判断搜索结果是支持、削弱还是中性。必须严格 JSON。"""
    payload={"hypothesis":{"title":hypothesis.title,"description":hypothesis.description},"task_query":task.query,"schema":{"items":[{"index":0,"effect":"support|weaken|neutral","confidence":"0-1","reason":"一句话原因"}]},"search_results":[{"index":i,"title":x.get('title',''),"url":x.get('url',''),"snippet":(x.get('content') or x.get('snippet') or '')[:500]} for i,x in enumerate(items[:5])]}
    obj=services._llm_json(db,system,json.dumps(payload,ensure_ascii=False),temperature=0.05) or {}
    rows=obj.get('items') or []
    out=[]
    for i,_ in enumerate(items):
        row=next((r for r in rows if int(r.get('index',-1))==i),{}) if isinstance(rows,list) else {}
        effect=str(row.get('effect') or 'neutral').lower()
        if effect not in {'support','weaken','neutral'}: effect='neutral'
        try: conf=float(row.get('confidence') or 0.45)
        except Exception: conf=0.45
        out.append({'effect':effect,'confidence':max(0,min(1,conf)),'reason':str(row.get('reason') or '')[:500]})
    return out

def run_next_validation_round(db:Session, project_id:int, limit:int=2):
    ensure_tables()
    p=db.get(models.MvpProject, project_id)
    if not p: raise ValueError('project_not_found')
    tasks=db.query(models.ProgressEvidenceTask).filter_by(project_id=p.id).filter(models.ProgressEvidenceTask.status.in_(['pending','active'])).order_by(models.ProgressEvidenceTask.created_at.asc()).limit(limit).all()
    found=0
    for t in tasks:
        try:
            items=services.searxng_search(db,t.query,limit=3)
            h=db.get(models.ProgressHypothesis,t.hypothesis_id) if t.hypothesis_id else None
            judgments=_classify_evidence(db,h,t,items[:3])
            summaries=[]
            for idx,item in enumerate(items[:3]):
                url=item.get('url') or ''
                title=item.get('title') or item.get('content') or t.query
                snip=item.get('content') or item.get('snippet') or ''
                if not url and not title: continue
                j=judgments[idx] if idx < len(judgments) else {'effect':'neutral','confidence':0.45,'reason':''}
                e=models.ProgressEvidenceItem(project_id=p.id,hypothesis_id=t.hypothesis_id,task_id=t.id,title=title[:500],url=url,source_domain=_domain(url),snippet=snip[:1000],effect=j['effect'],reason=j.get('reason',''),confidence=j['confidence'])
                db.add(e); found+=1; summaries.append(f"{j['effect']}: {title[:100]}")
            t.status='done'; t.last_run_at=datetime.utcnow(); t.result_summary='；'.join(summaries[:3]) or '未发现明显证据'; db.merge(t)
            if h:
                db.flush()
                all_ev=db.query(models.ProgressEvidenceItem).filter_by(hypothesis_id=h.id).all(); h.evidence_count=len(all_ev); h.last_checked_at=datetime.utcnow()
                support=sum(1 for e in all_ev if e.effect=='support'); weaken=sum(1 for e in all_ev if e.effect=='weaken')
                h.status='supported' if support>=2 and support>weaken else ('weakened' if weaken>=2 and weaken>=support else 'unverified')
                h.confidence=min(0.9,max(0.15,0.25+support*0.15-weaken*0.12)); db.merge(h)
            db.commit()
        except Exception:
            db.rollback(); t.status='failed'; t.result_summary='验证失败'; db.merge(t); db.commit()
    for h in db.query(models.ProgressHypothesis).filter_by(project_id=p.id).all():
        all_ev=db.query(models.ProgressEvidenceItem).filter_by(hypothesis_id=h.id).all(); support=sum(1 for e in all_ev if e.effect=='support'); weaken=sum(1 for e in all_ev if e.effect=='weaken')
        h.evidence_count=len(all_ev); h.status='supported' if support>=2 and support>weaken else ('weakened' if weaken>=2 and weaken>=support else 'unverified'); h.confidence=min(0.9,max(0.15,0.25+support*0.15-weaken*0.12)); db.merge(h)
    p.next_action=f'已运行下一轮验证，新增/更新证据 {found} 条。继续查看假设状态和证据链。'; db.merge(p); db.commit()
    return get_project(db,project_id)

def validate_project(db:Session, project_id:int):
    ensure_tables()
    p=db.get(models.MvpProject, project_id)
    if not p: raise ValueError("project_not_found")
    if not (p.prd_content or "").strip(): raise ValueError("prd_required_before_validation")
    old_score=float(p.feasibility_score or 0)
    run=models.MvpValidationRun(project_id=p.id,kind="product_analysis",status="running")
    db.add(run); db.commit(); db.refresh(run)
    try:
        return _validate_inner(db, p, run, old_score)
    except Exception as e:
        import traceback; traceback.print_exc()
        err=str(e)[:2000]
        try:
            run.status="failed"; run.summary_json=json.dumps({"error":err,"old_score":old_score},ensure_ascii=False); run.finished_at=datetime.utcnow(); db.merge(run)
            p.status="analysis_failed"; p.next_action=f"产品分析失败：{err[:300]}。请检查后端日志或点击「重新分析」。"; db.merge(p)
            db.commit()
        except Exception:
            db.rollback()
        return run

def _validate_inner(db:Session, p, run, old_score):
    card=db.get(models.OpportunityCard,p.representative_card_id)
    group=services.opportunity_group_for_card(db,card) if card else {}
    card_detail=_card_detail(db,card)
    slim_card={k:card_detail[k] for k in ['title','keyword','verdict','score','demand_score','serp_gap_score','competitor_weakness_score','commercial_score','monetization_score','monetization_type','mvp_plan','business'] if k in (card_detail or {})}
    slim_card['risks']=(card_detail.get('risks') or [])[:5]
    biz=(card_detail or {}).get("business") or {}
    icp=biz.get("icp") or "potential customers"
    queries=_prd_competitor_queries(db,p,slim_card)
    system="""你是 PRD-first 的产品与商业化分析负责人。
核心原则：当前 PRD 是主事实源，必须优先分析 PRD 描述的新产品方案本身；原采纳机会和原证据只作为历史基线/需求来源参考，不能把分析重点变成“和原机会做对比”。如果 PRD 相比原机会发生 pivot，要明确说明 pivot 后的新 ICP、商业模式、分发入口、付费路径是否成立。
你必须围绕 PRD 回答：1) PRD 的核心产品 thesis 是什么；2) 目标用户/买方/使用方分别是谁；3) 核心工作流是否闭环；4) 商业逻辑是否成立；5) 付费路径和价格策略是否合理；6) 如果 PRD 包含服务商官网嵌入、白标、lead capture、CRM/export、销售简报等机制，必须专门分析该分发模式是否成立；7) 必须基于搜索得到的候选和 PRD 产品形态判断真正竞品，不要只使用 PRD 内提到的名字；8) 从竞品商业模式反推我们的风险、机会、可学习打法、应避开的战场；9) 第一批客户和第一笔钱如何验证；10) PRD 需要如何补强；11) 是否应该提高、保持或降低产品可行性评分。
评分规则：以 PRD 新方案为准。若新方案有更清晰 ICP、分发入口、付费理由、服务商价值和可验证 MVP，可升分；若 PRD 只是概念、价格不合理、服务商无付费动机、官网嵌入转化链条不清、获客不可执行，要降分或标记需改 PRD。不要只输出对比结论，必须剖析新方案。
竞品部分必须输出 competitor_landscape 和 competitor_table：先总结竞品格局/商业模式/风险/机会/可学习打法/应避开战场，再逐个分析竞品商业模式、获客、定价、对我们的风险、机会、可学习点。
必须中文，严格 JSON。"""
    competitors=_extract_competitors_from_serp(db,p,queries)
    snaps=[]  # keep synchronous PRD analysis fast; competitor pages can be probed in a later evidence task
    comp_payload=[{"domain":c.domain,"url":c.url,"notes":c.notes,"sitemap_url":c.sitemap_url} for c in competitors[:20]]
    sitemap_payload=[]
    for s in snaps[:20]:
        try: summary=json.loads(s.summary_json or "{}")
        except Exception: summary={}
        sitemap_payload.append({"competitor_id":s.competitor_id,"url_count":summary.get("url_count"),"interesting":summary.get("interesting",[])[:10]})
    user=json.dumps({"schema":{"feasibility_score":"0-100 after product analysis","score_change_reason":"为什么升分/降分/保持","risk_level":"low|medium|high|critical","verdict":"continue|need_evidence|adjust_prd|pause","decision_summary":{"decision":"继续推进|需要补证|需要改PRD|暂停","reason":"一句话主因","score_change_reason":"分数变化原因","biggest_opportunity":"最大机会","biggest_risk":"最大风险","next_step":"下一步动作"},"prd_core_thesis":{"product":"PRD里的新产品是什么","primary_customer":"谁付费/谁购买","end_user":"谁实际使用","distribution_model":"核心分发模式，例如服务商官网嵌入/白标/SEO/直销","why_this_can_work":"为什么这个新方案可能成立","main_breakpoint":"最可能断掉的环节"},"embedded_calculator_strategy":{"applies":"yes|no","website_embed_value":"嵌入服务商官网对服务商的价值","lead_capture_flow":"访客如何从计算器变成线索","service_provider_workflow":"服务商如何使用线索/报告/销售简报","integration_needs":"CRM/export/email/webhook/白标等需求","adoption_risk":"服务商不愿嵌入或不愿付费的原因","validation_test":"如何验证官网嵌入模式成立"},"pricing_strategy":{"proposed_price":"PRD中的价格/建议价格","buyer_value_anchor":"买方价值锚点","pricing_risk":"价格不合理或难成交的原因","recommended_test":"建议如何做价格测试","first_paid_offer":"第一笔钱应该卖什么套餐/服务"},"prd_reasonableness":{"verdict":"reasonable|needs_revision|weak","strengths":[],"problems":[],"missing_sections":[],"revision_advice":[]},"product_plan":{"positioning":"产品定位","core_workflow":"核心流程","mvp_scope":[],"must_not_build":[],"first_validation":"首个验证动作"},"target_users":[{"segment":"目标用户分群","pain":"痛点","payment_trigger":"付费触发","entry":"可触达入口/关键词/社区","evidence":"证据摘要","confidence":"low|medium|high"}],"commercial_logic":{"why_now":"为什么现在需要","value_proposition":"价值主张","business_model":"商业模式","budget_owner":"预算归属","main_assumption":"最大假设"},"payment_path":{"buyer":"谁付费","trigger":"何时付费","pricing_test":"定价测试","conversion_path":"从入口到付费路径","first_sale_test":"第一笔钱测试"},"competitor_landscape":{"market_structure":"这个市场的竞品格局/分层","dominant_business_models":["竞品主要商业模式"],"risk_to_us":["从竞品商业模式看我们的风险"],"opportunities_for_us":["从竞品缺口看我们的机会"],"what_to_learn":["值得学习的获客/定价/产品/销售打法"],"where_to_avoid":["不应该正面硬碰的战场"],"positioning_advice":"我们应该如何定位以避开强竞品并占住机会"},"competitor_table":[{"name":"竞品名","domain":"域名","url":"官网/证据链接","positioning":"定位","target_customer":"目标客户","business_model":"它怎么赚钱/收费对象/收入模式","pricing":"定价/收费信号","acquisition":"主要获客方式/渠道信号","core_features":["核心功能"],"maturity":"low|medium|high","strengths":["做得好的方面"],"weaknesses":["弱项/缺口"],"direct_competition":"none|indirect|direct","similarity":"low|medium|high","threat":"low|medium|high","moat":"壁垒/护城河","why_users_choose_them":"用户为什么会选它","why_users_leave":"用户为什么会不满意或离开","risk_to_us":"这个竞品对我们的具体风险","opportunity_for_us":"它暴露出的我们的机会","what_to_learn":"我们可以学习的地方","where_to_avoid":"需要避开的正面竞争点","our_wedge":"我们可切入/绕开的突破口","evidence":"用于判断的证据摘要","confidence":"low|medium|high"}],"acquisition_channels":[{"channel":"获客方式","entry":"入口/关键词/社区","test_action":"可执行验证动作","evidence":"证据","cost":"low|medium|high","confidence":"low|medium|high"}],"evidence_plan":[{"hypothesis":"待验证假设","current_evidence":"当前证据","method":"抓取/搜索/访谈/落地页测试","success_signal":"成功信号","priority":"high|medium|low"}],"wedge":"总体突破口/差异化入口；没有则说明没有","prd_gaps":[],"next_actions":[],"notification":"给用户的简短结论"},"prd":_short(p.prd_content,5000),"original_opportunity":slim_card,"opportunity_group":group,"evidence_queries":queries,"competitors":comp_payload,"sitemap":sitemap_payload},ensure_ascii=False)
    obj=None  # use compact PRD-first schema for stable synchronous analysis
    if not obj:
        compact_system="""你是PRD-first产品分析负责人。必须中文，严格JSON。重点分析PRD新方案和真实竞品商业模式。"""
        compact_user=json.dumps({"task":"基于PRD和搜索到的竞品候选，输出紧凑但完整的产品分析。必须分析竞品商业模式对我们的风险、机会、可学习点、应避开战场。","schema":{"feasibility_score":"0-100","risk_level":"low|medium|high|critical","verdict":"continue|need_evidence|adjust_prd|pause","decision_summary":{"decision":"结论","reason":"原因","score_change_reason":"评分变化原因","biggest_opportunity":"最大机会","biggest_risk":"最大风险","next_step":"下一步"},"prd_core_thesis":{"product":"产品是什么","primary_customer":"谁付费","end_user":"谁使用","distribution_model":"分发模式","why_this_can_work":"为什么成立","main_breakpoint":"最可能断点"},"embedded_calculator_strategy":{"applies":"yes|no","website_embed_value":"嵌入官网价值","lead_capture_flow":"线索流程","service_provider_workflow":"服务商工作流","adoption_risk":"采用风险","validation_test":"验证方式"},"pricing_strategy":{"proposed_price":"价格","buyer_value_anchor":"价值锚点","pricing_risk":"价格风险","recommended_test":"测试建议","first_paid_offer":"第一笔钱"},"competitor_landscape":{"market_structure":"格局","dominant_business_models":[],"risk_to_us":[],"opportunities_for_us":[],"what_to_learn":[],"where_to_avoid":[],"positioning_advice":"定位建议"},"competitor_table":[{"name":"竞品","domain":"域名","positioning":"定位","target_customer":"客户","business_model":"怎么赚钱","pricing":"定价","acquisition":"获客","strengths":[],"weaknesses":[],"direct_competition":"none|indirect|direct","threat":"low|medium|high","risk_to_us":"风险","opportunity_for_us":"机会","what_to_learn":"学习点","where_to_avoid":"避开点","our_wedge":"切入点","evidence":"证据"}],"prd_reasonableness":{"verdict":"reasonable|needs_revision|weak","strengths":[],"problems":[],"missing_sections":[],"revision_advice":[]},"product_plan":{"positioning":"产品定位","core_workflow":"核心流程","mvp_scope":[],"must_not_build":[],"first_validation":"首个验证动作"},"target_users":[{"segment":"用户分群","pain":"痛点","payment_trigger":"付费触发","entry":"触达入口","evidence":"证据","confidence":"low|medium|high"}],"commercial_logic":{"why_now":"为什么现在需要","value_proposition":"价值主张","business_model":"商业模式","budget_owner":"预算归属","main_assumption":"最大假设"},"payment_path":{"buyer":"谁付费","trigger":"何时付费","pricing_test":"定价测试","conversion_path":"转化路径","first_sale_test":"第一笔钱测试"},"acquisition_channels":[{"channel":"渠道","entry":"入口","test_action":"验证动作","cost":"low|medium|high","confidence":"low|medium|high"}],"evidence_plan":[{"hypothesis":"待验证假设","current_evidence":"当前证据","method":"验证方法","success_signal":"成功信号","priority":"high|medium|low"}],"prd_gaps":[],"next_actions":[],"notification":"简短结论"},"prd":_short(p.prd_content,2500),"original_opportunity":slim_card,"competitor_search_queries":queries,"competitor_candidates":comp_payload[:6]},ensure_ascii=False)
        obj=services._llm_json(db,compact_system,compact_user,temperature=0.1)
    if not obj:
        raise RuntimeError("LLM product analysis returned empty JSON")
    score=float(obj.get("feasibility_score") or 50)
    risk=str(obj.get("risk_level") or "medium")
    verdict=str(obj.get("verdict") or "need_evidence")
    p.feasibility_score=score; p.risk_level=risk; p.status=f"analysis_{verdict}"[:40]; p.last_validated_at=datetime.utcnow(); p.next_action="；".join(obj.get("next_actions") or [])[:1000] or obj.get("notification") or "查看产品分析结果，继续补证或调整 PRD。"
    db.merge(p)
    db.query(models.MvpStrategyRecommendation).filter_by(project_id=p.id).delete()
    analysis_blocks=[("score","score_change_reason","评分变化原因"),("prd","prd_core_thesis","PRD 核心方案"),("distribution","embedded_calculator_strategy","官网嵌入 / 服务商分发策略"),("pricing","pricing_strategy","价格策略分析"),("prd","prd_reasonableness","PRD 合理性"),("plan","product_plan","产品方案"),("customer","target_users","目标用户"),("commercial","commercial_logic","商业逻辑"),("payment","payment_path","付费路径"),("competitor","competitor_landscape","竞品格局 / 商业模式洞察"),("competitor","competitor_table","竞品多维分析"),("acquisition","acquisition_channels","获客方式"),("wedge","wedge","突破口 / 差异化"),("evidence","evidence_plan","下一步证据计划"),("prd","prd_gaps","PRD 待补强")]
    for typ,key,title in analysis_blocks:
        val=obj.get(key) or []
        content=json.dumps(val,ensure_ascii=False,indent=2) if isinstance(val,(list,dict)) else str(val)
        if content.strip(): db.add(models.MvpStrategyRecommendation(project_id=p.id,type=typ,title=title,content=content,confidence=score/100,status="open"))
    for typ,key,title in [("pricing","pricing_strategy","定价策略"),("seo","seo_strategy","SEO 策略"),("promotion","promotion_strategy","推广策略"),("iteration","iteration_strategy","迭代策略"),("prd","mvp_scope_changes","PRD/MVP 调整")]:
        val=obj.get(key) or []
        content="\n".join([str(x) for x in val]) if isinstance(val,list) else str(val)
        if content.strip(): db.add(models.MvpStrategyRecommendation(project_id=p.id,type=typ,title=title,content=content,confidence=score/100,status="open"))
    _seed_progress_loop(db,p,obj,queries)
    run.status="ok"; run.summary_json=json.dumps({"llm":bool(obj),"analysis_type":"product_analysis","queries":queries,"competitors":len(competitors),"sitemap_snapshots":len(snaps),"old_score":old_score,"new_score":score,"score_delta":score-old_score,"analysis":obj},ensure_ascii=False); run.score_delta=score-old_score; run.finished_at=datetime.utcnow(); db.merge(run)
    db.commit(); db.refresh(run); db.refresh(p); return run
