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

def list_projects(db:Session):
    ensure_tables()
    rows=db.query(models.MvpProject).order_by(models.MvpProject.updated_at.desc()).all()
    return [{"id":p.id,"opportunity_group_id":p.opportunity_group_id,"canonical_keyword":p.canonical_keyword,"representative_card_id":p.representative_card_id,"status":p.status,"prd_version":p.prd_version,"feasibility_score":p.feasibility_score,"risk_level":p.risk_level,"next_action":p.next_action,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat(),"last_validated_at":p.last_validated_at.isoformat() if p.last_validated_at else None} for p in rows]

def get_project(db:Session, project_id:int):
    ensure_tables()
    p=db.get(models.MvpProject, project_id)
    if not p: return None
    runs=db.query(models.MvpValidationRun).filter_by(project_id=p.id).order_by(models.MvpValidationRun.started_at.desc()).limit(20).all()
    competitors=db.query(models.TrackedCompetitor).filter_by(project_id=p.id).order_by(models.TrackedCompetitor.created_at.desc()).all()
    recs=db.query(models.MvpStrategyRecommendation).filter_by(project_id=p.id).order_by(models.MvpStrategyRecommendation.created_at.desc()).all()
    return {"project":list_projects(db=[].__class__) if False else {"id":p.id,"opportunity_group_id":p.opportunity_group_id,"canonical_keyword":p.canonical_keyword,"representative_card_id":p.representative_card_id,"status":p.status,"prd_path":p.prd_path,"prd_version":p.prd_version,"prd_content":p.prd_content,"feasibility_score":p.feasibility_score,"risk_level":p.risk_level,"next_action":p.next_action,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat(),"last_validated_at":p.last_validated_at.isoformat() if p.last_validated_at else None},"runs":[{"id":r.id,"kind":r.kind,"status":r.status,"summary":json.loads(r.summary_json or "{}"),"score_delta":r.score_delta,"started_at":r.started_at.isoformat(),"finished_at":r.finished_at.isoformat() if r.finished_at else None} for r in runs],"competitors":[{"id":c.id,"domain":c.domain,"name":c.name,"url":c.url,"pricing_url":c.pricing_url,"sitemap_url":c.sitemap_url,"status":c.status,"notes":c.notes,"last_seen_at":c.last_seen_at.isoformat() if c.last_seen_at else None} for c in competitors],"recommendations":[{"id":r.id,"type":r.type,"title":r.title,"content":r.content,"confidence":r.confidence,"status":r.status,"created_at":r.created_at.isoformat()} for r in recs]}

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
    p=models.MvpProject(opportunity_group_id=gid, canonical_keyword=group.get("canonical_keyword") or card.title, representative_card_id=card.id, status="needs_prd")
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
    p.prd_content=content; p.prd_path=str(path.relative_to(ROOT)); p.prd_version=(p.prd_version or 0)+1; p.status="prd_ready"; p.next_action="PRD 已保存，可以启动完整可行性验证。"
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
    run=models.MvpValidationRun(project_id=p.id,kind="full_validation",status="running")
    db.add(run); db.commit(); db.refresh(run)
    card=db.get(models.OpportunityCard,p.representative_card_id)
    group=services.opportunity_group_for_card(db,card) if card else {}
    queries=[p.canonical_keyword, f"{p.canonical_keyword} competitors", f"{p.canonical_keyword} alternatives", f"{p.canonical_keyword} pricing", f"{p.canonical_keyword} template", f"{p.canonical_keyword} calculator", f"{p.canonical_keyword} software"]
    system="你是机会推进验证负责人。基于 PRD、机会组证据、竞品/SERP/Sitemap 证据，判断 MVP 可行性，并给出 PRD、定价、SEO、推广、迭代建议。必须中文，严格 JSON。"
    competitors=_extract_competitors_from_serp(db,p,queries)
    snaps=_sitemap_probe(db,competitors)
    comp_payload=[{"domain":c.domain,"url":c.url,"notes":c.notes,"sitemap_url":c.sitemap_url} for c in competitors[:20]]
    sitemap_payload=[]
    for s in snaps[:20]:
        try: summary=json.loads(s.summary_json or "{}")
        except Exception: summary={}
        sitemap_payload.append({"competitor_id":s.competitor_id,"url_count":summary.get("url_count"),"interesting":summary.get("interesting",[])[:10]})
    user=json.dumps({"schema":{"feasibility_score":"0-100","risk_level":"low|medium|high|critical","verdict":"continue|adjust_prd|pause","prd_gaps":[],"competitor_findings":[],"serp_evidence_plan":[],"mvp_scope_changes":[],"pricing_strategy":[],"seo_strategy":[],"promotion_strategy":[],"iteration_strategy":[],"next_actions":[],"notification":"如果可行性降低或继续增强，给用户的简短通知"},"prd":p.prd_content,"opportunity_group":group,"competitors":comp_payload,"sitemap":sitemap_payload},ensure_ascii=False)
    obj=services._llm_json(db,system,user,temperature=0.15) or {}
    score=float(obj.get("feasibility_score") or 50)
    risk=str(obj.get("risk_level") or "medium")
    p.feasibility_score=score; p.risk_level=risk; p.status="validated"; p.last_validated_at=datetime.utcnow(); p.next_action="；".join(obj.get("next_actions") or [])[:1000] or obj.get("notification") or "查看策略建议并继续补证。"
    db.merge(p)
    for typ,key,title in [("pricing","pricing_strategy","定价策略"),("seo","seo_strategy","SEO 策略"),("promotion","promotion_strategy","推广策略"),("iteration","iteration_strategy","迭代策略"),("prd","mvp_scope_changes","PRD/MVP 调整")]:
        val=obj.get(key) or []
        content="\n".join([str(x) for x in val]) if isinstance(val,list) else str(val)
        if content.strip(): db.add(models.MvpStrategyRecommendation(project_id=p.id,type=typ,title=title,content=content,confidence=score/100,status="open"))
    run.status="ok"; run.summary_json=json.dumps({"llm":bool(obj),"queries":queries,"competitors":len(competitors),"sitemap_snapshots":len(snaps),"analysis":obj},ensure_ascii=False); run.score_delta=score-(p.feasibility_score or 0); run.finished_at=datetime.utcnow(); db.merge(run)
    db.commit(); db.refresh(run); db.refresh(p); return run
