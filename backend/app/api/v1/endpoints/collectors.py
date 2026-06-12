from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import collectors, models, schemas
from app.api.deps import obj
from app.core.security import require_auth
from app.database import get_db

router = APIRouter(prefix="/api/collectors", tags=["collectors"])


def _json_value(value: str, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _result_errors(result: dict) -> list:
    errors = result.get("errors") if isinstance(result, dict) else []
    if isinstance(errors, list):
        return errors
    if errors:
        return [errors]
    return []


def _input_refs(inputs: dict) -> list[dict]:
    refs: list[dict] = []
    groups = (
        ("seeds", "keyword"),
        ("topics", "keyword"),
        ("roots", "keyword"),
        ("queries", "keyword"),
        ("domains", "domain"),
    )
    for field, typ in groups:
        values = inputs.get(field) if isinstance(inputs, dict) else []
        if isinstance(values, str):
            values = [values]
        for index, value in enumerate(values or []):
            text = str(value or "").strip()
            if text:
                refs.append({"type": typ, "value": text, "field": field, "index": index})
    return refs


def _norm_text(value: str) -> str:
    return str(value or "").strip().lower().removeprefix("https://").removeprefix("http://").removeprefix("www.")


def _match_input_ref(values: list[str], refs: list[dict]) -> dict | None:
    normalized = [_norm_text(v) for v in values if str(v or "").strip()]
    for ref in refs:
        ref_value = _norm_text(ref.get("value", ""))
        if ref_value and ref_value in normalized:
            return ref
    for ref in refs:
        ref_value = _norm_text(ref.get("value", ""))
        if not ref_value:
            continue
        if any(ref_value in value or value in ref_value for value in normalized if value):
            return ref
    if len(refs) == 1:
        return refs[0]
    return None


def _candidate_input_ref(candidate: dict, refs: list[dict]) -> dict:
    evidence = candidate.get("evidence") if isinstance(candidate.get("evidence"), dict) else {}
    values = [
        evidence.get("inputRef", {}).get("value") if isinstance(evidence.get("inputRef"), dict) else "",
        evidence.get("seed"),
        evidence.get("topic"),
        evidence.get("root"),
        evidence.get("query"),
        evidence.get("domain"),
        evidence.get("seed_domain"),
        evidence.get("source_domain"),
        candidate.get("source_domain"),
        evidence.get("url"),
        candidate.get("source_url"),
    ]
    ref = _match_input_ref([str(v) for v in values if v], refs)
    if ref:
        return dict(ref)
    return {"type": "unknown", "value": "", "field": "", "index": None, "missing": True}


def _enrich_candidate(candidate: dict, refs: list[dict]) -> dict:
    out = dict(candidate)
    evidence = out.get("evidence") if isinstance(out.get("evidence"), dict) else {}
    ref = _candidate_input_ref(out, refs)
    out["inputRef"] = ref
    evidence["inputRef"] = ref
    out["evidence"] = evidence
    return out


def _persist_candidate_input_refs(db: Session, candidates: list[dict]) -> None:
    for item in candidates:
        ref = item.get("inputRef") or {}
        if not item.get("id") or ref.get("missing"):
            continue
        row = db.get(models.CandidateKeyword, int(item["id"]))
        if not row:
            continue
        try:
            evidence = json.loads(row.evidence_json or "{}")
        except Exception:
            evidence = {}
        evidence["inputRef"] = ref
        row.evidence_json = json.dumps(evidence, ensure_ascii=False)
        db.merge(row)


def _normalize_errors(result: dict, inputs: dict) -> list[dict]:
    refs = _input_refs(inputs)
    normalized = []
    for err in _result_errors(result):
        if isinstance(err, dict):
            values = [err.get("seed"), err.get("topic"), err.get("root"), err.get("query"), err.get("domain"), err.get("url")]
            ref = _match_input_ref([str(v) for v in values if v], refs) or (refs[0] if len(refs) == 1 else None)
            message = err.get("error") or err.get("message") or err.get("reason") or json.dumps(err, ensure_ascii=False)
            normalized.append({**err, "message": str(message), "inputRef": ref or {"type": "unknown", "value": "", "field": "", "index": None, "missing": True}, "retryable": bool(err.get("retryable", True))})
        else:
            normalized.append({"message": str(err), "inputRef": refs[0] if len(refs) == 1 else {"type": "unknown", "value": "", "field": "", "index": None, "missing": True}, "retryable": True})
    return normalized


def _normalize_run_output(db: Session, inputs: dict, result: dict) -> dict:
    refs = _input_refs(inputs)
    output = dict(result or {})
    raw_candidates = output.get("generatedClues") or output.get("candidates") or []
    if not isinstance(raw_candidates, list):
        raw_candidates = []
    generated = [_enrich_candidate(item, refs) for item in raw_candidates if isinstance(item, dict)]
    output["generatedClues"] = generated
    output["candidates"] = generated
    output.setdefault("candidates_created", len(generated))
    output["errors"] = _normalize_errors(output, inputs)
    _persist_candidate_input_refs(db, generated)
    return output


def _created_count(result: dict) -> int:
    for key in ("saved", "imported", "candidates_created", "evidence_created"):
        if result.get(key) is not None:
            try:
                return int(result.get(key) or 0)
            except Exception:
                return 0
    return 0


def _candidate_marker(db: Session) -> int:
    row = db.query(models.CandidateKeyword.id).order_by(models.CandidateKeyword.id.desc()).first()
    return int(row[0]) if row else 0


def _candidate_obj(row: models.CandidateKeyword) -> dict:
    d = obj(row)
    try:
        d["evidence"] = json.loads(row.evidence_json or "{}")
    except Exception:
        d["evidence"] = {}
    return d


def _new_candidates(db: Session, after_id: int, inputs: dict | None = None, limit: int = 100) -> list[dict]:
    rows = (
        db.query(models.CandidateKeyword)
        .filter(models.CandidateKeyword.id > after_id)
        .order_by(models.CandidateKeyword.id.desc())
        .limit(max(1, min(300, limit)))
        .all()
    )
    refs = _input_refs(inputs or {})
    return [_enrich_candidate(_candidate_obj(row), refs) for row in rows]


def _record_source_run(db: Session, source: str, run_kind: str, inputs: dict, result: dict, source_role: str = "demand") -> dict:
    result = _normalize_run_output(db, inputs, result)
    errors = result.get("errors") or []
    now = datetime.utcnow()
    row = models.SourceRun(
        source=source,
        source_role=source_role,
        run_kind=run_kind,
        status="failed" if not result.get("ok", True) else ("warning" if errors else "ok"),
        inputs_json=json.dumps(inputs, ensure_ascii=False),
        outputs_json=json.dumps(result, ensure_ascii=False),
        candidates_created=_created_count(result),
        errors=json.dumps(errors, ensure_ascii=False),
        started_at=now,
        finished_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    result["source_run_id"] = row.id
    return result


def _record_manual_collector_run(db: Session, source: str, inputs: dict, runner) -> dict:
    marker = _candidate_marker(db)
    result = runner()
    result.setdefault("candidates", _new_candidates(db, marker, inputs))
    return _record_source_run(db, result.get("source") or source, "manual", inputs, result)


def _source_run_obj(row: models.SourceRun) -> dict:
    d = obj(row)
    d["inputs"] = _json_value(row.inputs_json, {})
    d["outputs"] = _json_value(row.outputs_json, {})
    d["errors"] = _json_value(row.errors, [])
    return d

@router.get("/candidates")
def candidate_list(limit: int = 100, status: str = "new", _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    q = db.query(models.CandidateKeyword)
    if status:
        q = q.filter(models.CandidateKeyword.status == status)
    rows = q.order_by(models.CandidateKeyword.score.desc(), models.CandidateKeyword.created_at.desc()).limit(limit).all()
    out=[]
    for r in rows:
        d=obj(r)
        try: d["evidence"] = json.loads(r.evidence_json or "{}")
        except Exception: d["evidence"] = {}
        out.append(d)
    return out

@router.get("/rejected-reasons")
def rejected_reasons(limit: int = 500, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.rejected_candidate_reasons(db, limit=limit)

@router.post("/candidates/rejected/cleanup")
def rejected_cleanup(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    if payload.get('preview'):
        return collectors.preview_cleanup_rejected_candidates(db, keep_latest=max(0, int(payload.get('keep_latest') or 300)))
    return collectors.cleanup_rejected_candidates(db, keep_latest=max(0, int(payload.get('keep_latest') or 300)), force=bool(payload.get('force')))

@router.post("/repairs/missing-tool-intent")
def repair_missing_tool_intent(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    if payload.get('preview'):
        return collectors.preview_missing_tool_intent_repair(db)
    return collectors.apply_missing_tool_intent_repair(db, force=bool(payload.get('force')))

@router.post("/repairs/generic-short-tail")
def repair_generic_short_tail(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    if payload.get('preview'):
        return collectors.preview_generic_short_tail_repair(db, limit=max(1, int(payload.get('limit') or 300)))
    return collectors.apply_generic_short_tail_repair(db, limit=max(1, int(payload.get('limit') or 300)), max_rewrites=max(1, int(payload.get('max_rewrites') or 40)), force=bool(payload.get('force')))

@router.post("/repairs/sitemap-editorial-path")
def repair_sitemap_editorial_path(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    if payload.get('preview'):
        return collectors.preview_sitemap_editorial_path_repair(db, limit=max(1, int(payload.get('limit') or 500)))
    return collectors.apply_sitemap_editorial_path_repair(db, limit=max(1, int(payload.get('limit') or 500)), force=bool(payload.get('force')))

@router.get("/summary")
def collector_summary(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_pool_summary(db)

@router.get("/health")
def collector_health(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_system_health(db)

@router.get("/targets")
def collector_targets(limit: int = 120, status: str = "active", _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    q = db.query(models.CollectorTarget)
    if status:
        q = q.filter(models.CollectorTarget.status == status)
    return [obj(r) for r in q.order_by(models.CollectorTarget.priority.desc(), models.CollectorTarget.created_at.desc()).limit(limit).all()]

@router.post("/targets/refresh")
def collector_targets_refresh(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.refresh_collector_targets_from_cards(db)

@router.post("/targets/health")
def collector_targets_health(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.apply_collector_target_health(db)

@router.get("/targets/segments")
def collector_targets_segments(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_target_segments(db)

@router.get("/matrix")
def collector_condition_matrix(limit: int = 300, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_condition_source_matrix(db, limit=max(1, min(1000, limit)))

@router.get("/budget/next")
def collector_budget_next(limit: int = 24, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_next_budget(db, limit=max(1, limit))

@router.get("/runs")
def collector_runs(limit: int = 10, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.RunHistory).filter_by(kind='collector_autopilot').order_by(models.RunHistory.started_at.desc()).limit(max(1, min(50, limit))).all()
    return [obj(r) for r in rows]

@router.get("/source-runs")
def collector_source_runs(limit: int = 50, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.SourceRun).order_by(models.SourceRun.started_at.desc()).limit(max(1, min(200, limit))).all()
    return [_source_run_obj(r) for r in rows]

@router.get("/source-runs/stats")
def collector_source_run_stats(_: bool = Depends(require_auth), db: Session = Depends(get_db)):
    by_source: dict[str, dict[str, int]] = {}
    totals = {"runs": 0, "seen": 0, "leads": 0, "errors": 0}
    def add_source(source: str, seen: int = 0, leads: int = 0, errors: int = 0) -> None:
        source = source or "unknown"
        bucket = by_source.setdefault(source, {"runs": 0, "seen": 0, "leads": 0, "errors": 0})
        values = {"runs": 1, "seen": int(seen or 0), "leads": int(leads or 0), "errors": int(errors or 0)}
        for key, value in values.items():
            bucket[key] += value
            totals[key] += value

    for row in db.query(models.RunHistory).filter_by(kind="collector_autopilot").all():
        summary = _json_value(row.summary, {})
        source_results = summary.get("source_results") if isinstance(summary, dict) else []
        if not isinstance(source_results, list):
            continue
        for item in source_results:
            if not isinstance(item, dict):
                continue
            add_source(item.get("source") or "unknown", item.get("seen") or 0, item.get("saved") or 0, item.get("errors") or 0)

    rows = db.query(models.SourceRun).all()
    for row in rows:
        outputs = _json_value(row.outputs_json, {})
        errors = _json_value(row.errors, [])
        seen = 0
        if isinstance(outputs, dict):
            for key in ("seen", "urls_seen", "pages_seen", "candidates_seen"):
                if outputs.get(key) is not None:
                    seen = int(outputs.get(key) or 0)
                    break
        error_count = len(errors) if isinstance(errors, list) else (1 if errors else 0)
        add_source(row.source or "unknown", seen, int(row.candidates_created or 0), error_count)
    return {"by_source": by_source, "totals": totals}

@router.get("/repairs")
def collector_repairs(limit: int = 10, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.RunHistory).filter_by(kind='collector_repair').order_by(models.RunHistory.started_at.desc()).limit(max(1, min(50, limit))).all()
    out=[]
    for r in rows:
        d=obj(r)
        try:
            result=(d.get('summary') or {}).get('result') or {}
            if result and not result.get('repair_safety'):
                result['repair_safety']=collectors.repair_safety_score(result)
                d['summary']['result']=result
        except Exception:
            pass
        out.append(d)
    return out

@router.post("/repairs/autopilot")
def repair_autopilot(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    return collectors.run_safe_repair_autopilot(db, allow_cleanup=bool(payload.get('allow_cleanup')), force=bool(payload.get('force')))

@router.get("/repairs/autopilot/runs")
def repair_autopilot_runs(limit: int = 8, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.RunHistory).filter_by(kind='collector_repair_autopilot').order_by(models.RunHistory.started_at.desc()).limit(max(1,min(30,limit))).all()
    return [obj(r) for r in rows]

@router.get("/autopilot/report")
def collector_autopilot_report(run_id: int | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_autopilot_self_repair_report(db, run_id=run_id)

@router.get("/roi")
def collector_roi(limit: int = 12, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_roi_stats(db, limit=max(1, min(50, limit)))

@router.get("/roi/recommendations")
def collector_roi_recommendations(limit: int = 12, min_runs: int = 2, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.collector_roi_weight_recommendations(db, limit=max(1, min(50, limit)), min_runs=max(1, min_runs))

@router.post("/roi/apply")
def collector_roi_apply(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    return collectors.apply_collector_roi_weight_recommendations(db, limit=max(1, min(50, int(payload.get('limit') or 12))), min_runs=max(1, int(payload.get('min_runs') or 2)))

@router.get("/roi/applications")
def collector_roi_applications(limit: int = 10, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    rows=db.query(models.RunHistory).filter_by(kind='collector_roi_weights').order_by(models.RunHistory.started_at.desc()).limit(max(1, min(50, limit))).all()
    return [obj(r) for r in rows]

@router.post("/targets/{target_id}/status")
def collector_target_status(target_id: int, payload: dict, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    row=db.get(models.CollectorTarget, target_id)
    if not row: raise HTTPException(status_code=404, detail="target not found")
    status=str(payload.get('status') or '').strip()
    if status not in {'active','cooldown','rejected','exhausted'}:
        raise HTTPException(status_code=400, detail="invalid status")
    row.status=status
    if status=='active':
        row.reject_count=0
    if payload.get('note'):
        row.notes=((row.notes or '') + ' | ' + str(payload.get('note'))[:160])[:800]
    db.merge(row); db.commit(); db.refresh(row)
    return obj(row)

@router.get("/targets/{target_id}/outputs")
def collector_target_outputs(target_id: int, limit: int = 80, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    target=db.get(models.CollectorTarget, target_id)
    if not target: raise HTTPException(status_code=404, detail="target not found")
    needle=f'"collector_target_ids":'
    candidates=[]
    for c in db.query(models.CandidateKeyword).order_by(models.CandidateKeyword.created_at.desc()).limit(800).all():
        try: ev=json.loads(c.evidence_json or '{}')
        except Exception: ev={}
        ids=ev.get('collector_target_ids') or []
        if target_id in ids:
            candidates.append({**obj(c), 'evidence': ev})
            if len(candidates)>=limit: break
    keywords=[]
    for kw in db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(800).all():
        try: meta=json.loads(kw.root_terms or '{}') if (kw.root_terms or '').strip().startswith('{') else {}
        except Exception: meta={}
        ids=meta.get('collector_target_ids') or []
        if target_id in ids:
            cards=[]
            for card in db.query(models.OpportunityCard).filter_by(keyword_id=kw.id).order_by(models.OpportunityCard.created_at.desc()).all():
                cards.append(obj(card))
            keywords.append({**obj(kw), 'root_meta': meta, 'cards': cards})
            if len(keywords)>=limit: break
    return {'target': obj(target), 'candidates': candidates, 'keywords': keywords, 'cards': [card for kw in keywords for card in kw.get('cards', [])]}

@router.post("/autopilot/run")
def collector_autopilot_run(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    marker = _candidate_marker(db)
    result = collectors.run_collector_autopilot(db, limit=max(1, payload.limit), import_limit=max(1, payload.limit // 2 or 1))
    if not result.get("enabled", True):
        return result
    inputs = {
        "seeds": result.get("seeds") or result.get("auto_targets", {}).get("keywords") or [],
        "domains": result.get("domains") or result.get("auto_targets", {}).get("domains") or [],
        "limit": payload.limit,
        "import_limit": max(1, payload.limit // 2 or 1),
    }
    result.setdefault("candidates", _new_candidates(db, marker, inputs))
    return _record_source_run(db, "autopilot", "auto", inputs, result)

@router.post("/sitemap/run")
def sitemap_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    inputs = {"domains": domains, "max_urls_per_domain": payload.max_urls_per_domain, "only_new": payload.only_new}
    return _record_manual_collector_run(db, "sitemap", inputs, lambda: collectors.run_sitemap_watcher(db, domains, payload.max_urls_per_domain, payload.only_new))

@router.post("/domain-web/run")
def domain_web_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    max_pages = min(12, max(1, payload.max_urls_per_domain // 10))
    return _record_manual_collector_run(db, "domain_web", {"domains": domains, "max_pages_per_domain": max_pages}, lambda: collectors.run_domain_web_collector(db, domains, max_pages_per_domain=max_pages))

@router.post("/alternatives/run")
def alternatives_run(payload: schemas.CollectorSitemapIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    domains=[d.strip() for d in payload.domains if d.strip()]
    return _record_manual_collector_run(db, "alternatives", {"domains": domains}, lambda: collectors.run_alternatives_collector(db, domains))

@router.post("/suggest/run")
def suggest_run(payload: schemas.CollectorSuggestIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    seeds=[s.strip() for s in payload.seeds if s.strip()]
    return _record_manual_collector_run(db, "suggest", {"seeds": seeds}, lambda: collectors.run_suggest_collector(db, seeds))

@router.post("/advanced-search/run")
def advanced_search_run(payload: schemas.CollectorAdvancedSearchIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    roots=[x.strip() for x in payload.roots if x.strip()]
    domains=[x.strip() for x in payload.domains if x.strip()]
    inputs = {"roots": roots, "domains": domains, "days": payload.days, "limit_per_query": payload.limit_per_query}
    return _record_manual_collector_run(db, "advanced_search", inputs, lambda: collectors.run_advanced_search_collector(db, roots, domains, payload.days, payload.limit_per_query))

@router.post("/source-radar/run")
def source_radar_run(payload: schemas.CollectorSourceRadarIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    seeds=[x.strip() for x in payload.seeds if x.strip()]
    inputs = {"seeds": seeds, "limit_per_seed": payload.limit_per_seed}
    return _record_manual_collector_run(db, "source_radar", inputs, lambda: collectors.run_source_radar(db, seeds, payload.limit_per_seed))

@router.post("/hot-topic/run")
def hot_topic_run(payload: schemas.CollectorSuggestIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    topics=[x.strip() for x in payload.seeds if x.strip()]
    return _record_manual_collector_run(db, "hot_topic", {"topics": topics}, lambda: collectors.run_hot_topic_collector(db, topics or None))

@router.post("/candidates/clean")
def candidate_clean(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.clean_candidate_pool(db, max(1, payload.limit))

@router.post("/candidates/import")
def candidate_import(payload: schemas.CandidateImportIn, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    return collectors.import_candidates_to_keywords(db, payload.limit)

@router.post("/keywords/auto-verify")
def collector_keywords_auto_verify(payload: dict | None = None, _: bool = Depends(require_auth), db: Session = Depends(get_db)):
    payload=payload or {}
    return collectors.auto_verify_collector_keywords(db, limit=max(1, int(payload.get('limit') or 8)), min_score=float(payload.get('min_score') or 0.72))
