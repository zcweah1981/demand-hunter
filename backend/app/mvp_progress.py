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
    for cls in [models.MvpProject, models.MvpValidationRun, models.TrackedCompetitor, models.CompetitorSnapshot, models.MvpStrategyRecommendation]:
        cls.__table__.create(bind=engine, checkfirst=True)

def slugify(s:str)->str:
    return re.sub(r"[^a-z0-9]+","-",(s or "project").lower()).strip("-")[:80] or "project"

def _card_obj(db:Session, card:models.OpportunityCard):
    kw=db.get(models.Keyword, card.keyword_id)
    group=services.opportunity_group_for_card(db, card)
    return {"card_id":card.id,"keyword":kw.query if kw else card.title,"verdict":card.verdict,"feedback_label":card.feedback_label,"score":card.score,"group":group}

def _json_loads(s, default):
    try: return json.loads(s or "")
    except Exception: return default

def _short(s:str, n:int=50000)->str:
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
    original=float(card.score or 0) if card else 0.0
    display_score=float(p.feasibility_score or original or 0)
    return {"project":list_projects(db=[].__class__) if False else {"id":p.id,"opportunity_group_id":p.opportunity_group_id,"canonical_keyword":p.canonical_keyword,"representative_card_id":p.representative_card_id,"status":p.status,"prd_path":p.prd_path,"prd_version":p.prd_version,"prd_content":p.prd_content,"feasibility_score":display_score,"original_score":original,"score_delta":round(display_score-original,1) if p.last_validated_at else 0,"risk_level":p.risk_level,"next_action":p.next_action,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat(),"last_validated_at":p.last_validated_at.isoformat() if p.last_validated_at else None,"opportunity":_card_detail(db,card)},"runs":[{"id":r.id,"kind":r.kind,"status":r.status,"summary":json.loads(r.summary_json or "{}"),"score_delta":r.score_delta,"started_at":r.started_at.isoformat(),"finished_at":r.finished_at.isoformat() if r.finished_at else None} for r in runs],"competitors":[{"id":c.id,"domain":c.domain,"name":c.name,"url":c.url,"pricing_url":c.pricing_url,"sitemap_url":c.sitemap_url,"status":c.status,"notes":c.notes,"last_seen_at":c.last_seen_at.isoformat() if c.last_seen_at else None} for c in competitors],"recommendations":[{"id":r.id,"type":r.type,"title":r.title,"content":r.content,"confidence":r.confidence,"status":r.status,"created_at":r.created_at.isoformat()} for r in recs]}

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

def _extract_competitors_from_serp(db:Session, project:models.MvpProject, queries:list[str]):
    out=[]; seen=set()
    for q in queries[:8]:
        kw=models.Keyword(query=q[:250], source="mvp_progress", intent="competitor_discovery", score=0.0)
        # do not insert keyword; use search provider directly via run_serp needs DB keyword, so temporary commit then keep as evidence keyword
        try:
            db.add(kw); db.commit(); db.refresh(kw)
            serp=services.run_serp(db, kw)
            for s in serp[:8]:
                d=_domain(s.url)
                if not d or d in seen: continue
                seen.add(d)
                c=db.query(models.TrackedCompetitor).filter_by(project_id=project.id, domain=d).first()
                if not c:
                    c=models.TrackedCompetitor(project_id=project.id,domain=d,name=s.title[:250],url=s.url,pricing_url="",sitemap_url=f"https://{d}/sitemap.xml",notes=f"来自搜索：{q}",last_seen_at=datetime.utcnow())
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

def validate_project(db:Session, project_id:int):
    ensure_tables()
    p=db.get(models.MvpProject, project_id)
    if not p: raise ValueError("project_not_found")
    if not (p.prd_content or "").strip(): raise ValueError("prd_required_before_validation")
    old_score=float(p.feasibility_score or 0)
    run=models.MvpValidationRun(project_id=p.id,kind="product_analysis",status="running")
    db.add(run); db.commit(); db.refresh(run)
    card=db.get(models.OpportunityCard,p.representative_card_id)
    group=services.opportunity_group_for_card(db,card) if card else {}
    card_detail=_card_detail(db,card)
    biz=(card_detail or {}).get("business") or {}
    icp=biz.get("icp") or "potential customers"
    queries=[p.canonical_keyword, f"{p.canonical_keyword} competitors", f"{p.canonical_keyword} alternatives", f"{p.canonical_keyword} pricing", f"{p.canonical_keyword} template", f"{p.canonical_keyword} calculator", f"{p.canonical_keyword} software", f"{p.canonical_keyword} reddit", f"{icp} {p.canonical_keyword}"]
    system="""你是机会推进的产品分析负责人。目标不是执行 MVP，而是先判断 PRD 是否合理，再基于真实证据重新判断方案是否值得推进。
你必须判断：1) PRD 本身是否合理、是否继承了原采纳机会；2) 目标用户是否清晰且有真实需求入口；3) 商业逻辑是否成立；4) 付费路径是否合理；5) SERP/竞品/潜在客户证据是否支持这个方案；6) 竞品是否强势到没有突破口；7) 是否存在差异化 wedge；8) 获客方式是否可执行；9) PRD 需要如何补强；10) 是否应该提高、保持或降低可行性评分。
评分规则：竞品强且同质化/无入口/无客户证据要降分；发现明确痛点、弱竞品、可触达客户、清晰突破口要升分；证据不足要标 Need Evidence 或降低置信。
必须中文，严格 JSON。"""
    competitors=_extract_competitors_from_serp(db,p,queries)
    snaps=_sitemap_probe(db,competitors)
    comp_payload=[{"domain":c.domain,"url":c.url,"notes":c.notes,"sitemap_url":c.sitemap_url} for c in competitors[:20]]
    sitemap_payload=[]
    for s in snaps[:20]:
        try: summary=json.loads(s.summary_json or "{}")
        except Exception: summary={}
        sitemap_payload.append({"competitor_id":s.competitor_id,"url_count":summary.get("url_count"),"interesting":summary.get("interesting",[])[:10]})
    user=json.dumps({"schema":{"feasibility_score":"0-100 after product analysis","score_change_reason":"为什么升分/降分/保持","risk_level":"low|medium|high|critical","verdict":"continue|need_evidence|adjust_prd|pause","decision_summary":{"decision":"继续推进|需要补证|需要改PRD|暂停","reason":"一句话主因","score_change_reason":"分数变化原因","biggest_opportunity":"最大机会","biggest_risk":"最大风险","next_step":"下一步动作"},"prd_reasonableness":{"verdict":"reasonable|needs_revision|weak","strengths":[],"problems":[],"missing_sections":[],"revision_advice":[]},"product_plan":{"positioning":"产品定位","core_workflow":"核心流程","mvp_scope":[],"must_not_build":[],"first_validation":"首个验证动作"},"target_users":[{"segment":"目标用户分群","pain":"痛点","payment_trigger":"付费触发","entry":"可触达入口/关键词/社区","evidence":"证据摘要","confidence":"low|medium|high"}],"commercial_logic":{"why_now":"为什么现在需要","value_proposition":"价值主张","business_model":"商业模式","budget_owner":"预算归属","main_assumption":"最大假设"},"payment_path":{"buyer":"谁付费","trigger":"何时付费","pricing_test":"定价测试","conversion_path":"从入口到付费路径","first_sale_test":"第一笔钱测试"},"competitor_table":[{"name":"竞品名","domain":"域名","url":"官网/证据链接","positioning":"定位","target_customer":"目标客户","core_features":["核心功能"],"pricing":"定价/收费信号","maturity":"low|medium|high","strengths":["做得好的方面"],"weaknesses":["弱项/缺口"],"direct_competition":"none|indirect|direct","similarity":"low|medium|high","threat":"low|medium|high","moat":"壁垒/护城河","acquisition":"主要获客方式/渠道信号","why_users_choose_them":"用户为什么会选它","why_users_leave":"用户为什么会不满意或离开","our_wedge":"我们可切入/绕开的突破口","evidence":"用于判断的证据摘要","confidence":"low|medium|high"}],"acquisition_channels":[{"channel":"获客方式","entry":"入口/关键词/社区","test_action":"可执行验证动作","evidence":"证据","cost":"low|medium|high","confidence":"low|medium|high"}],"evidence_plan":[{"hypothesis":"待验证假设","current_evidence":"当前证据","method":"抓取/搜索/访谈/落地页测试","success_signal":"成功信号","priority":"high|medium|low"}],"wedge":"总体突破口/差异化入口；没有则说明没有","prd_gaps":[],"next_actions":[],"notification":"给用户的简短结论"},"prd":_short(p.prd_content),"original_opportunity":card_detail,"opportunity_group":group,"evidence_queries":queries,"competitors":comp_payload,"sitemap":sitemap_payload},ensure_ascii=False)
    obj=services._llm_json(db,system,user,temperature=0.15) or {}
    score=float(obj.get("feasibility_score") or 50)
    risk=str(obj.get("risk_level") or "medium")
    verdict=str(obj.get("verdict") or "need_evidence")
    p.feasibility_score=score; p.risk_level=risk; p.status=f"analysis_{verdict}"[:40]; p.last_validated_at=datetime.utcnow(); p.next_action="；".join(obj.get("next_actions") or [])[:1000] or obj.get("notification") or "查看产品分析结果，继续补证或调整 PRD。"
    db.merge(p)
    db.query(models.MvpStrategyRecommendation).filter_by(project_id=p.id).delete()
    analysis_blocks=[("score","score_change_reason","评分变化原因"),("prd","prd_reasonableness","PRD 合理性"),("plan","product_plan","产品方案"),("customer","target_users","目标用户"),("commercial","commercial_logic","商业逻辑"),("payment","payment_path","付费路径"),("competitor","competitor_table","竞品多维分析"),("acquisition","acquisition_channels","获客方式"),("wedge","wedge","突破口 / 差异化"),("evidence","evidence_plan","下一步证据计划"),("prd","prd_gaps","PRD 待补强")]
    for typ,key,title in analysis_blocks:
        val=obj.get(key) or []
        content=json.dumps(val,ensure_ascii=False,indent=2) if isinstance(val,(list,dict)) else str(val)
        if content.strip(): db.add(models.MvpStrategyRecommendation(project_id=p.id,type=typ,title=title,content=content,confidence=score/100,status="open"))
    for typ,key,title in [("pricing","pricing_strategy","定价策略"),("seo","seo_strategy","SEO 策略"),("promotion","promotion_strategy","推广策略"),("iteration","iteration_strategy","迭代策略"),("prd","mvp_scope_changes","PRD/MVP 调整")]:
        val=obj.get(key) or []
        content="\n".join([str(x) for x in val]) if isinstance(val,list) else str(val)
        if content.strip(): db.add(models.MvpStrategyRecommendation(project_id=p.id,type=typ,title=title,content=content,confidence=score/100,status="open"))
    run.status="ok"; run.summary_json=json.dumps({"llm":bool(obj),"analysis_type":"product_analysis","queries":queries,"competitors":len(competitors),"sitemap_snapshots":len(snaps),"old_score":old_score,"new_score":score,"score_delta":score-old_score,"analysis":obj},ensure_ascii=False); run.score_delta=score-old_score; run.finished_at=datetime.utcnow(); db.merge(run)
    db.commit(); db.refresh(run); db.refresh(p); return run
