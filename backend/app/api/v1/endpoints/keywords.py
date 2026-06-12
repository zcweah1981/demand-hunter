from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, services
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/keywords", tags=["keywords"])

@router.post("/discover")
def discover(payload: schemas.DailyRunIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    if payload.use_four_find:
        return [obj(k) for k in services.discover_keywords_four_find(db, payload.limit, payload.seeds)]
    return [obj(k) for k in services.discover_keywords(db, payload.limit, payload.roots)]

@router.get("")
def keywords(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(k) for k in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(200).all()]

@router.post("")
def add_keyword(payload: schemas.KeywordIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row = db.query(models.Keyword).filter_by(query=payload.query).first()
    if not row:
        row = models.Keyword(query=payload.query, source=payload.source, root_terms=json.dumps(payload.root_terms), intent=services.classify_intent(payload.query))
        db.add(row)
        db.commit()
        db.refresh(row)
    return obj(row)

@router.get("/{keyword_id}")
def keyword_detail(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, keyword_id)
    if not kw:
        raise HTTPException(404, "keyword not found")
    return {
        "keyword": obj(kw),
        "serp": [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()],
        "competitors": [obj(x) for x in db.query(models.CompetitorPage).filter_by(keyword_id=keyword_id).all()],
        "social": [obj(x) for x in db.query(models.SocialEvidence).filter_by(keyword_id=keyword_id).all()],
        "cards": [obj(x) for x in db.query(models.OpportunityCard).filter_by(keyword_id=keyword_id).order_by(models.OpportunityCard.created_at.desc()).all()],
    }

def _strings(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

@router.post("/{keyword_id}/llm-analysis")
def keyword_llm_analysis(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, keyword_id)
    if not kw:
        raise HTTPException(404, "keyword not found")
    serp = [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).limit(8).all()]
    competitors = [obj(x) for x in db.query(models.CompetitorPage).filter_by(keyword_id=keyword_id).limit(8).all()]
    social = [obj(x) for x in db.query(models.SocialEvidence).filter_by(keyword_id=keyword_id).limit(8).all()]
    cards = [obj(x) for x in db.query(models.OpportunityCard).filter_by(keyword_id=keyword_id).order_by(models.OpportunityCard.created_at.desc()).limit(3).all()]
    system = (
        "你是 Demand Hunter 的关键词客观研判助手。只返回 JSON。"
        "不要用系统已有评分反向论证，不要编造外部事实。"
        "只基于关键词文本、SERP 摘要、竞品弱点、社区证据和机会记录，给出独立客观判断。"
        "JSON 字段必须包含 verdict, summary, long_term_fit, demand_interpretation, risks, evidence_to_collect, next_actions。"
    )
    user = json.dumps({
        "task": "判断这个入库关键词是否值得继续自动搜索分析、补证据或生成机会。",
        "keyword": obj(kw),
        "serp_results": serp,
        "competitor_weaknesses": competitors,
        "social_evidence": social,
        "opportunity_cards": cards,
    }, ensure_ascii=False)
    result = services._llm_json(db, system, user, temperature=0.15)
    if not result:
        return {"ok": False, "status": "llm_unavailable", "source": "none", "analysis": None, "message": "LLM 未配置或未返回有效 JSON，当前没有生成关键词研判。"}
    return {
        "ok": True,
        "status": "ok",
        "source": "llm",
        "analysis": {
            "verdict": str(result.get("verdict") or result.get("recommendation") or "需继续观察"),
            "summary": str(result.get("summary") or ""),
            "long_term_fit": str(result.get("long_term_fit") or result.get("fit") or "unknown"),
            "demand_interpretation": str(result.get("demand_interpretation") or result.get("demand") or ""),
            "risks": _strings(result.get("risks")),
            "evidence_to_collect": _strings(result.get("evidence_to_collect") or result.get("evidence_gaps")),
            "next_actions": _strings(result.get("next_actions")),
            "provider": result.get("_llm_provider"),
        },
    }

@router.post("/{keyword_id}/serp/run")
def run_serp(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, keyword_id)
    if not kw:
        raise HTTPException(404, "keyword not found")
    return [obj(x) for x in services.run_serp(db, kw)]

@router.get("/{keyword_id}/serp")
def get_serp(keyword_id: int, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return [obj(x) for x in db.query(models.SerpResult).filter_by(keyword_id=keyword_id).order_by(models.SerpResult.rank).all()]
