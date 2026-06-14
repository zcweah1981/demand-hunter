from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from . import collectors, evidence_system, four_find, models, services


ExecutionResult = dict[str, Any]
Executor = Callable[[Session, dict[str, Any]], ExecutionResult]


def _json_loads(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _payload_list(payload: dict[str, Any], key: str, setting_key: str | None = None, db: Session | None = None) -> list[str]:
    value = payload.get(key) or []
    if isinstance(value, str):
        items = [x.strip() for x in value.replace(",", "\n").splitlines() if x.strip()]
    elif isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
    else:
        items = []
    if not items and setting_key and db is not None:
        items = [x.strip() for x in (services.setting(db, setting_key) or "").replace(",", "\n").splitlines() if x.strip()]
    return items


def _input_refs(values: list[str], ref_type: str) -> list[dict[str, str]]:
    return [{"type": ref_type, "label": value} for value in values]


def _event(
    db: Session,
    request_id: int | None,
    event_type: str,
    target_type: str,
    target_id: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if not request_id:
        return
    db.add(
        models.ActionEvent(
            request_id=request_id,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            payload_json=_json_dumps(payload or {}),
        )
    )


def _ok(action: dict[str, Any], summary: str, **extra: Any) -> ExecutionResult:
    return {
        "ok": True,
        "status": "success",
        "action_type": action.get("action_type"),
        "target_type": action.get("target_type"),
        "target_id": str(action.get("target_id") or ""),
        "summary": summary,
        **extra,
    }


def _failed(action: dict[str, Any], summary: str, error: str, retryable: bool = True, **extra: Any) -> ExecutionResult:
    return {
        "ok": False,
        "status": "failed",
        "action_type": action.get("action_type"),
        "target_type": action.get("target_type"),
        "target_id": str(action.get("target_id") or ""),
        "summary": summary,
        "errors": [{"message": error, "retryable": retryable}],
        **extra,
    }


def _candidate_marker(db: Session) -> int:
    row = db.query(models.CandidateKeyword.id).order_by(models.CandidateKeyword.id.desc()).first()
    return int(row[0]) if row else 0


def _keyword_marker(db: Session) -> int:
    row = db.query(models.Keyword.id).order_by(models.Keyword.id.desc()).first()
    return int(row[0]) if row else 0


def _discovery_expansion_marker(db: Session) -> int:
    row = db.query(models.DiscoveryExpansion.id).order_by(models.DiscoveryExpansion.id.desc()).first()
    return int(row[0]) if row else 0


def _competitor_keyword_marker(db: Session) -> int:
    row = db.query(models.CompetitorKeyword.id).order_by(models.CompetitorKeyword.id.desc()).first()
    return int(row[0]) if row else 0


def _competitor_site_marker(db: Session) -> int:
    row = db.query(models.CompetitorSite.id).order_by(models.CompetitorSite.id.desc()).first()
    return int(row[0]) if row else 0


def _new_keywords(db: Session, after_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        db.query(models.Keyword)
        .filter(models.Keyword.id > after_id)
        .order_by(models.Keyword.id.asc())
        .limit(max(1, min(300, limit)))
        .all()
    )
    return [{"id": row.id, "query": row.query, "source": row.source, "status": row.status, "score": row.score} for row in rows]


def _new_discovery_expansions(db: Session, after_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        db.query(models.DiscoveryExpansion)
        .filter(models.DiscoveryExpansion.id > after_id)
        .order_by(models.DiscoveryExpansion.id.asc())
        .limit(max(1, min(300, limit)))
        .all()
    )
    return [
        {
            "id": row.id,
            "text": row.expanded_keyword,
            "keyword": row.expanded_keyword,
            "source_model": f"four_find:{row.expansion_type or 'keyword_to_keyword'}",
            "status": row.status,
            "score": row.score,
            "inputRef": {"type": "seed", "label": row.seed_keyword},
        }
        for row in rows
    ]


def _new_competitor_keywords(db: Session, after_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        db.query(models.CompetitorKeyword)
        .filter(models.CompetitorKeyword.id > after_id)
        .order_by(models.CompetitorKeyword.id.asc())
        .limit(max(1, min(300, limit)))
        .all()
    )
    return [
        {
            "id": row.id,
            "text": row.discovered_keyword,
            "keyword": row.discovered_keyword,
            "source_model": "four_find:site_to_keyword",
            "status": row.status,
            "score": row.score,
            "inputRef": {"type": "domain", "label": row.competitor_domain},
        }
        for row in rows
    ]


def _new_competitor_sites(db: Session, after_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        db.query(models.CompetitorSite)
        .filter(models.CompetitorSite.id > after_id)
        .order_by(models.CompetitorSite.id.asc())
        .limit(max(1, min(300, limit)))
        .all()
    )
    return [
        {
            "id": row.id,
            "domain": row.similar_domain,
            "title": row.title,
            "source_model": "four_find:site_to_site",
            "inputRef": {"type": "domain", "label": row.seed_domain},
        }
        for row in rows
    ]


def _new_candidates(db: Session, after_id: int, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        db.query(models.CandidateKeyword)
        .filter(models.CandidateKeyword.id > after_id)
        .order_by(models.CandidateKeyword.id.desc())
        .limit(max(1, min(300, limit)))
        .all()
    )
    output: list[dict[str, Any]] = []
    for row in rows:
        item = {
            "id": row.id,
            "text": row.keyword,
            "keyword": row.keyword,
            "type": "search_keyword",
            "source_model": row.source,
            "source": row.source,
            "status": row.status,
            "score": row.score,
        }
        try:
            evidence = json.loads(row.evidence_json or "{}")
        except Exception:
            evidence = {}
        input_ref = evidence.get("inputRef") if isinstance(evidence.get("inputRef"), dict) else None
        if not input_ref:
            value = str(evidence.get("seed") or evidence.get("query") or evidence.get("domain") or evidence.get("url") or "")
            if value:
                ref_type = "domain" if "." in value and " " not in value else "keyword"
                input_ref = {"type": ref_type, "value": value, "label": value}
        item["inputRef"] = input_ref or {"type": "unknown", "value": "", "missing": True}
        output.append(item)
    return output


def _record_source_run(
    db: Session,
    source: str,
    run_kind: str,
    action: dict[str, Any],
    result: dict[str, Any],
    source_role: str = "automation",
    started_at: datetime | None = None,
) -> models.SourceRun:
    now = datetime.utcnow()
    started = started_at or now
    payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
    errors = _normalize_result_errors(result.get("errors"), payload)
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    raw_result = result.get("raw_result") if isinstance(result.get("raw_result"), dict) else {}
    outputs = {**raw_result, **result}
    inputs = {
        **payload,
        "action_type": action.get("action_type"),
        "target_type": action.get("target_type"),
        "target_id": str(action.get("target_id") or ""),
    }
    row = models.SourceRun(
        source=source or str(action.get("action_type") or "automation"),
        source_role=source_role,
        run_mode=str(action.get("source") or "system"),
        run_kind=run_kind or str(action.get("action_type") or "automation"),
        target_type=str(action.get("target_type") or ""),
        target_id=str(action.get("target_id") or ""),
        status="failed" if not result.get("ok", True) else ("warning" if errors else "ok"),
        inputs_json=_json_dumps(inputs),
        outputs_json=_json_dumps(outputs),
        candidates_created=int(metrics.get("generated_clues") or len(result.get("generatedClues") or [])),
        evidence_created=int(metrics.get("evidence_created") or len(result.get("generatedEvidence") or [])),
        keywords_promoted=int(metrics.get("keywords_promoted") or len(result.get("generatedKeywords") or [])),
        cards_generated=int(metrics.get("cards_generated") or len(result.get("generatedOpportunities") or [])),
        actions_created=int(metrics.get("actions_created") or len(result.get("nextActions") or [])),
        errors=_json_dumps(errors),
        duration_ms=max(0, int((now - started).total_seconds() * 1000)),
        started_at=started,
        finished_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _normalize_result_errors(errors: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(errors, list):
        return []
    input_refs = payload.get("inputRefs") if isinstance(payload.get("inputRefs"), list) else []
    normalized: list[dict[str, Any]] = []
    for item in errors:
        if isinstance(item, str):
            normalized.append({"message": item, "inputRef": {"type": "unknown", "value": ""}, "retryable": True})
            continue
        if not isinstance(item, dict):
            normalized.append({"message": str(item), "inputRef": {"type": "unknown", "value": ""}, "retryable": True})
            continue
        message = str(item.get("message") or item.get("error") or item.get("reason") or item)
        value = str(item.get("seed") or item.get("domain") or item.get("query") or item.get("url") or item.get("input") or "")
        input_ref = item.get("inputRef") if isinstance(item.get("inputRef"), dict) else None
        if not input_ref and value:
            input_ref = next(
                (
                    ref
                    for ref in input_refs
                    if isinstance(ref, dict)
                    and str(ref.get("value") or ref.get("label") or "") == value
                ),
                None,
            )
        if not input_ref:
            input_ref = {"type": "keyword" if value and "." not in value else "domain" if value else "unknown", "value": value}
        normalized.append({**item, "message": message, "inputRef": input_ref, "retryable": bool(item.get("retryable", True))})
    return normalized


def _target_ref(db: Session, target_type: str, target_id: str) -> dict[str, Any]:
    if target_type in {"keyword", "keywords"} and target_id.isdigit():
        row = db.get(models.Keyword, int(target_id))
        if row:
            return {"type": "keyword", "id": row.id, "label": row.query, "source": row.source}
    if target_type in {"clue", "candidate_keyword"} and target_id.isdigit():
        row = db.get(models.CandidateKeyword, int(target_id))
        if row:
            return {"type": "candidate_keyword", "id": row.id, "label": row.keyword, "source": row.source}
    if target_type in {"candidate_entry", "entry"} and target_id.isdigit():
        row = db.get(models.CandidateEntry, int(target_id))
        if row:
            return {"type": "candidate_entry", "id": row.id, "label": row.name, "source": row.source}
    if target_type in {"opportunity_card", "opportunity"} and target_id.isdigit():
        row = db.get(models.OpportunityCard, int(target_id))
        if row:
            return {"type": "opportunity_card", "id": row.id, "label": row.title, "source": "opportunity"}
    if target_type in {"watch_target", "watch"} and target_id.isdigit():
        row = db.get(models.WatchTarget, int(target_id))
        if row:
            return {"type": "watch_target", "id": row.id, "label": row.target_key, "source": row.target_type}
    return {"type": target_type or "unknown", "id": target_id, "label": target_id, "missing": True}


def _create_evidence_for_keyword(db: Session, keyword: models.Keyword, created_by: str) -> list[dict[str, Any]]:
    generated: list[dict[str, Any]] = []
    serp_rows = db.query(models.SerpResult).filter_by(keyword_id=keyword.id).order_by(models.SerpResult.rank).limit(10).all()
    if not serp_rows:
        try:
            services.run_serp_with_strategy(db, keyword)
        except Exception:
            serp_rows = []
        else:
            serp_rows = db.query(models.SerpResult).filter_by(keyword_id=keyword.id).order_by(models.SerpResult.rank).limit(10).all()
    for serp in serp_rows:
        item = evidence_system.create_evidence_item(
            db,
            source_type="serp_result",
            source_name=serp.domain or "SERP",
            url=serp.url,
            title=serp.title,
            summary=serp.snippet,
            raw_json={"keyword_id": keyword.id, "rank": serp.rank, "gap_tags": serp.gap_tags},
            confidence=0.65,
        )
        link = evidence_system.link_evidence(db, item.id, "keyword", keyword.id, "search_result", f"SERP 结果 #{serp.rank}", created_by=created_by)
        generated.append({"id": item.id, "link_id": link.id, "source_type": item.source_type, "title": item.title, "url": item.url})

    for social in services.collect_social(db, keyword):
        item = evidence_system.create_evidence_item(
            db,
            source_type="community",
            source_name=social.platform,
            url=social.url,
            title=social.title,
            summary=social.snippet,
            raw_json={"keyword_id": keyword.id, "platform": social.platform},
            confidence=0.7,
        )
        link = evidence_system.link_evidence(db, item.id, "keyword", keyword.id, "community_signal", "社区/社交讨论旁证", created_by=created_by)
        generated.append({"id": item.id, "link_id": link.id, "source_type": item.source_type, "title": item.title, "url": item.url})

    for competitor in services.analyze_competitors(db, keyword):
        item = evidence_system.create_evidence_item(
            db,
            source_type="competitor_page",
            source_name=competitor.domain,
            url=competitor.url,
            title=competitor.title,
            summary=competitor.content_excerpt,
            raw_json={"keyword_id": keyword.id, "weakness_tags": competitor.weakness_tags},
            confidence=0.6,
        )
        link = evidence_system.link_evidence(db, item.id, "keyword", keyword.id, "competitor_gap", "竞品弱点/内容缺口", created_by=created_by)
        generated.append({"id": item.id, "link_id": link.id, "source_type": item.source_type, "title": item.title, "url": item.url})
    if not generated:
        item = evidence_system.create_evidence_item(
            db,
            source_type=keyword.source or "keyword",
            source_name="keyword_snapshot",
            title=keyword.query,
            summary="补证据动作记录了当前关键词对象；后续 SERP、社区或竞品证据会继续关联到该关键词。",
            raw_json={"keyword_id": keyword.id, "status": keyword.status, "score": keyword.score},
            confidence=0.35,
        )
        link = evidence_system.link_evidence(db, item.id, "keyword", keyword.id, "target_snapshot", "补证据动作关联的关键词快照", created_by=created_by)
        generated.append({"id": item.id, "link_id": link.id, "source_type": item.source_type, "title": item.title, "url": item.url})
    return generated


def _create_target_snapshot_evidence(db: Session, target_type: str, target_id: str, created_by: str) -> list[dict[str, Any]]:
    if target_type in {"keyword", "keywords"} and target_id.isdigit():
        keyword = db.get(models.Keyword, int(target_id))
        return _create_evidence_for_keyword(db, keyword, created_by) if keyword else []
    ref = _target_ref(db, target_type, target_id)
    if ref.get("missing"):
        return []
    source_type = str(ref.get("source") or target_type or "manual")
    item = evidence_system.create_evidence_item(
        db,
        source_type=source_type,
        source_name=str(ref.get("type") or target_type),
        title=str(ref.get("label") or target_id),
        summary=f"为 {target_type} #{target_id} 记录补证据请求时的当前对象快照。",
        raw_json={"target": ref},
        confidence=0.4,
    )
    link = evidence_system.link_evidence(db, item.id, target_type, target_id, "target_snapshot", "补证据动作关联的对象快照", created_by=created_by)
    return [{"id": item.id, "link_id": link.id, "source_type": item.source_type, "title": item.title, "url": item.url}]


def _legacy_daily(db: Session, action: dict[str, Any]) -> ExecutionResult:
    payload = action.get("payload") or {}
    try:
        limit = int(payload.get("limit") or services.setting(db, "AUTO_RUN_LIMIT") or "6")
    except Exception:
        limit = 6
    run = services.daily_run(db, limit=max(1, min(50, limit)), trigger=str(payload.get("trigger") or "automation_cycle"))
    summary = _json_loads(run.summary, run.summary)
    return _ok(
        action,
        "旧机会发现流程已执行",
        run_id=run.id,
        run_status=run.status,
        legacy_daily=summary,
        generatedOpportunities=(summary or {}).get("cards", []) if isinstance(summary, dict) else [],
    )


def _clue_model_run(db: Session, action: dict[str, Any]) -> ExecutionResult:
    payload = action.get("payload") or {}
    model = str(payload.get("model") or action.get("target_id") or "").strip().lower()
    marker = _candidate_marker(db)
    keyword_marker = _keyword_marker(db)
    input_refs: list[dict[str, str]] = []
    result: dict[str, Any]
    if model in {"autopilot", "collector_autopilot", "all"}:
        try:
            limit = int(payload.get("limit") or services.setting(db, "COLLECTOR_AUTO_LIMIT") or "24")
        except Exception:
            limit = 24
        try:
            import_limit = int(payload.get("import_limit") or services.setting(db, "COLLECTOR_AUTO_IMPORT_LIMIT") or "12")
        except Exception:
            import_limit = 12
        result = collectors.run_collector_autopilot(db, limit=max(1, limit), import_limit=max(1, import_limit))
        input_refs = _input_refs(_payload_list(payload, "seeds", "COLLECTOR_AUTO_SEEDS", db), "seed") + _input_refs(
            _payload_list(payload, "domains", "COLLECTOR_AUTO_DOMAINS", db), "domain"
        )
    elif model in {"suggest", "google_suggest", "keyword_to_keyword"}:
        seeds = _payload_list(payload, "seeds", "COLLECTOR_AUTO_SEEDS", db)
        input_refs = _input_refs(seeds, "seed")
        result = collectors.run_suggest_collector(db, seeds)
    elif model == "sitemap":
        domains = _payload_list(payload, "domains", "COLLECTOR_AUTO_DOMAINS", db)
        input_refs = _input_refs(domains, "domain")
        result = collectors.run_sitemap_watcher(db, domains, int(payload.get("max_urls_per_domain") or 80), bool(payload.get("only_new", True)))
    elif model in {"domain_web", "domain-web", "site_to_keyword"}:
        domains = _payload_list(payload, "domains", "COLLECTOR_AUTO_DOMAINS", db)
        input_refs = _input_refs(domains, "domain")
        result = collectors.run_domain_web_collector(db, domains, max_pages_per_domain=int(payload.get("max_pages_per_domain") or 8))
    elif model in {"alternative", "alternatives", "site_to_site"}:
        domains = _payload_list(payload, "domains", "COLLECTOR_AUTO_DOMAINS", db)
        input_refs = _input_refs(domains, "domain")
        result = collectors.run_alternatives_collector(db, domains)
    elif model in {"hot_topic", "hot-topic", "hot", "early_signal"}:
        topics = _payload_list(payload, "topics") or _payload_list(payload, "seeds", "COLLECTOR_AUTO_SEEDS", db)
        input_refs = _input_refs(topics, "topic")
        result = collectors.run_hot_topic_collector(db, topics or None, max_seconds=int(payload.get("max_seconds") or services.setting(db, "COLLECTOR_HOT_TOPIC_MAX_SECONDS") or 20))
    elif model in {"advanced_search", "advanced-search", "serp_search", "serp-search", "keyword_to_site"}:
        roots = _payload_list(payload, "roots") or _payload_list(payload, "seeds", "COLLECTOR_AUTO_SEEDS", db)
        domains = _payload_list(payload, "domains", "COLLECTOR_AUTO_DOMAINS", db)
        input_refs = _input_refs(roots, "seed") + _input_refs(domains, "domain")
        result = collectors.run_advanced_search_collector(
            db,
            roots,
            domains,
            days=int(payload.get("days") or 45),
            limit_per_query=int(payload.get("limit_per_query") or 5),
            max_seconds=int(payload.get("max_seconds") or services.setting(db, "COLLECTOR_ADVANCED_MAX_SECONDS") or 90),
        )
    elif model in {"source_radar", "source-radar", "hn_algolia", "arxiv", "github", "product_hunt", "steam"}:
        seeds = _payload_list(payload, "seeds", "COLLECTOR_AUTO_SEEDS", db)
        input_refs = _input_refs(seeds, "seed")
        result = collectors.run_source_radar(
            db,
            seeds,
            limit_per_seed=int(payload.get("limit_per_seed") or 6),
            max_seconds=int(payload.get("max_seconds") or services.setting(db, "COLLECTOR_SOURCE_RADAR_MAX_SECONDS") or 45),
        )
    elif model in {"four_find", "four-find", "four_find_full"}:
        seeds = _payload_list(payload, "seeds", "FOUR_FIND_AUTO_SEEDS", db)
        if not seeds:
            return _failed(action, "四找模型缺少 seed 输入", "missing_four_find_seeds", retryable=False)
        input_refs = _input_refs(seeds, "seed")
        keywords = services.discover_keywords_four_find(db, limit=int(payload.get("limit") or 12), seeds=seeds)
        result = {
            "ok": True,
            "source": "four_find",
            "seeds": len(seeds),
            "saved": len(keywords),
            "candidates_seen": len(keywords),
            "errors": [],
        }
    elif model in {"root_combo", "root-combo", "root"}:
        roots = _payload_list(payload, "roots") or _payload_list(payload, "seeds")
        input_refs = _input_refs(roots, "seed")
        keywords = services.discover_keywords(db, limit=int(payload.get("limit") or 24), roots=roots or None)
        result = {
            "ok": True,
            "source": "root_combo",
            "roots": len(roots),
            "saved": len(keywords),
            "candidates_seen": len(keywords),
            "errors": [],
        }
    else:
        return _failed(action, "线索模型未接入执行器", f"unsupported_clue_model:{model or 'empty'}", retryable=False)

    generated = _new_candidates(db, marker)
    generated_keywords = _new_keywords(db, keyword_marker)
    output = _ok(
        action,
        f"线索模型 {model or 'autopilot'} 已运行",
        metrics={
            "generated_clues": len(generated),
            "generated_keywords": len(generated_keywords),
            "raw_seen": result.get("seen") or result.get("urls_seen") or result.get("saved") or 0,
        },
        generatedClues=generated,
        candidates=generated,
        generatedKeywords=generated_keywords,
        inputRefs=payload.get("inputRefs") or input_refs,
        raw_result=result,
        errors=result.get("errors") or [],
    )
    source_name = result.get("source") or ("autopilot" if model in {"all", "autopilot", "collector_autopilot"} else model) or "collector"
    requested_by = _action_requested_by(db, payload)
    if model in {"all", "autopilot", "collector_autopilot"}:
        run_kind = "auto"
    elif requested_by == "api":
        run_kind = "manual"
    else:
        run_kind = "clue_model.run"
    source_run = _record_source_run(db, source_name, run_kind, action, output, source_role="demand")
    output["source_run_id"] = source_run.id
    return output


def _action_requested_by(db: Session, payload: dict[str, Any]) -> str:
    request_id = payload.get("request_id")
    if isinstance(request_id, int) or (isinstance(request_id, str) and request_id.isdigit()):
        row = db.get(models.ActionRequest, int(request_id))
        if row:
            return str(row.requested_by or "")
    return ""


def _four_find_run(db: Session, action: dict[str, Any]) -> ExecutionResult:
    payload = action.get("payload") or {}
    operation = str(payload.get("operation") or action.get("target_id") or "").strip().lower()
    expansion_marker = _discovery_expansion_marker(db)
    competitor_keyword_marker = _competitor_keyword_marker(db)
    competitor_site_marker = _competitor_site_marker(db)
    keyword_marker = _keyword_marker(db)
    input_refs: list[dict[str, Any]] = []
    result: dict[str, Any] = {"ok": True}

    if operation in {"expand", "keyword_to_keyword"}:
        seed = str(payload.get("seed") or "").strip()
        if not seed:
            return _failed(action, "四找词找词缺少 seed", "missing_seed", retryable=False)
        input_refs = [{"type": "seed", "label": seed}]
        rows = four_find.expand_by_suggest(db, seed, services.searxng_search) + four_find.expand_by_related(db, seed, services.searxng_search)
        result = {"ok": True, "operation": operation, "expanded_keywords": [row.expanded_keyword for row in rows]}
    elif operation in {"find_sites", "keyword_to_site"}:
        seed = str(payload.get("seed") or payload.get("keyword") or "").strip()
        if not seed:
            return _failed(action, "四找词找站缺少搜索词", "missing_keyword", retryable=False)
        input_refs = [{"type": "seed", "label": seed}]
        sites = four_find.find_sites_from_keyword(db, seed, services.searxng_search)
        result = {"ok": True, "operation": operation, "sites": sites}
    elif operation in {"site_keywords", "site_to_keyword"}:
        domain = str(payload.get("domain") or "").strip()
        if not domain:
            return _failed(action, "四找站找词缺少域名", "missing_domain", retryable=False)
        input_refs = [{"type": "domain", "label": domain}]
        rows = four_find.find_keywords_from_site(db, domain, services.searxng_search)
        result = {"ok": True, "operation": operation, "competitor_keywords": [{"id": row.id, "keyword": row.discovered_keyword} for row in rows]}
    elif operation in {"similar_sites", "site_to_site"}:
        domain = str(payload.get("domain") or "").strip()
        if not domain:
            return _failed(action, "四找站找站缺少域名", "missing_domain", retryable=False)
        input_refs = [{"type": "domain", "label": domain}]
        rows = four_find.find_similar_sites(db, domain, services.searxng_search)
        result = {"ok": True, "operation": operation, "similar_sites": [{"id": row.id, "domain": row.similar_domain} for row in rows]}
    elif operation in {"run", "full"}:
        seed = str(payload.get("seed") or "").strip()
        if not seed:
            return _failed(action, "完整四找缺少 seed", "missing_seed", retryable=False)
        input_refs = [{"type": "seed", "label": seed}]
        result = four_find.run_four_find(db, seed, services.searxng_search, depth=int(payload.get("depth") or 2))
        result["ok"] = True
        result["operation"] = operation
    elif operation in {"run_and_import", "full_import"}:
        seed = str(payload.get("seed") or "").strip()
        if not seed:
            return _failed(action, "四找导入流水线缺少 seed", "missing_seed", retryable=False)
        input_refs = [{"type": "seed", "label": seed}]
        result = four_find.run_four_find_and_import(
            db,
            seed,
            services.searxng_search,
            depth=int(payload.get("depth") or 2),
            import_limit=int(payload.get("import_limit") or 12),
        )
        result["ok"] = True
        result["operation"] = operation
    elif operation == "import_expansion":
        target_id = str(action.get("target_id") or payload.get("id") or "")
        row = four_find.import_expansion_to_keywords(db, int(target_id)) if target_id.isdigit() else None
        if not row:
            return _failed(action, "词找词结果导入失败", "expansion_not_found_or_already_rejected", retryable=False)
        input_refs = [{"type": "discovery_expansion", "id": target_id, "label": row.query}]
        result = {"ok": True, "operation": operation, "imported_keywords": [{"id": row.id, "query": row.query, "source": row.source}]}
    elif operation == "import_competitor_keyword":
        target_id = str(action.get("target_id") or payload.get("id") or "")
        row = four_find.import_competitor_keyword(db, int(target_id)) if target_id.isdigit() else None
        if not row:
            return _failed(action, "站找词结果导入失败", "competitor_keyword_not_found_or_already_rejected", retryable=False)
        input_refs = [{"type": "competitor_keyword", "id": target_id, "label": row.query}]
        result = {"ok": True, "operation": operation, "imported_keywords": [{"id": row.id, "query": row.query, "source": row.source}]}
    elif operation == "import_discovered":
        seed = str(payload.get("seed") or "").strip()
        rows = four_find.import_discovered_keywords(db, seed_keyword=seed or None, limit=int(payload.get("import_limit") or 12))
        input_refs = [{"type": "seed", "label": seed}] if seed else []
        result = {"ok": True, "operation": operation, "imported_keywords": [{"id": row.id, "query": row.query, "source": row.source} for row in rows]}
    elif operation == "prune":
        result = four_find.prune_low_quality_discoveries(db)
        result["ok"] = True
        result["operation"] = operation
    elif operation == "recover_serp_rejects":
        result = services.recover_serp_rejects(db, limit=int(payload.get("limit") or 8))
        result["ok"] = True
        result["operation"] = operation
    else:
        return _failed(action, "四找动作未接入执行器", f"unsupported_four_find_operation:{operation or 'empty'}", retryable=False)

    generated_clues = _new_discovery_expansions(db, expansion_marker) + _new_competitor_keywords(db, competitor_keyword_marker)
    generated_sites = _new_competitor_sites(db, competitor_site_marker)
    generated_keywords = _new_keywords(db, keyword_marker)
    next_actions = [
        {"action_type": "keyword.serp_analysis", "target_type": "keyword", "target_id": str(row["id"]), "reason": "four_find_imported_keyword"}
        for row in generated_keywords
    ]
    output = _ok(
        action,
        f"四找动作已执行：{operation}",
        metrics={
            "generated_clues": len(generated_clues),
            "generated_sites": len(generated_sites),
            "generated_keywords": len(generated_keywords),
        },
        inputRefs=input_refs,
        generatedClues=generated_clues,
        generatedSites=generated_sites,
        generatedKeywords=generated_keywords,
        raw_result=result,
        errors=result.get("errors") or [],
        nextActions=next_actions,
    )
    source_run = _record_source_run(db, "four_find", f"four_find.{operation}", action, output, source_role="demand")
    output["source_run_id"] = source_run.id
    return output


def _clue_score(db: Session, action: dict[str, Any]) -> ExecutionResult:
    payload = action.get("payload") or {}
    try:
        limit = int(payload.get("limit") or services.setting(db, "COLLECTOR_AUTO_IMPORT_LIMIT") or "12")
    except Exception:
        limit = 12
    keyword_marker = _keyword_marker(db)
    clean = collectors.clean_candidate_pool(db, max(1, min(200, limit * 2)))
    imported = collectors.import_candidates_to_keywords(db, max(1, min(100, limit)))
    promoted_keywords = _new_keywords(db, keyword_marker)
    output = _ok(
        action,
        "线索评分与关键词入库已执行",
        metrics={
            "clean_scanned": clean.get("scanned", 0),
            "imported": imported.get("imported", 0),
            "auto_verified": 0,
        },
        raw_result={"clean": clean, "imported": imported, "verified": {"skipped": "keyword_serp_executor_handles_next_stage"}},
        generatedKeywords=promoted_keywords,
        nextActions=[
            {"action_type": "keyword.serp_analysis", "target_type": "keyword", "target_id": str(row["id"])}
            for row in promoted_keywords
        ],
    )
    source_run = _record_source_run(db, "clue_score", "clue.score", action, output, source_role="demand")
    output["source_run_id"] = source_run.id
    return output


def _keyword_serp_analysis(db: Session, action: dict[str, Any]) -> ExecutionResult:
    target_id = str(action.get("target_id") or "")
    keyword = None
    if target_id.isdigit():
        keyword = db.get(models.Keyword, int(target_id))
    if not keyword and target_id and target_id != "all":
        keyword = db.query(models.Keyword).filter(models.Keyword.query == target_id).first()
    if not keyword:
        keyword = (
            db.query(models.Keyword)
            .filter(models.Keyword.status.in_(["new", "action", "watch"]))
            .order_by(models.Keyword.score.desc(), models.Keyword.created_at.asc())
            .first()
        )
    if not keyword:
        return _ok(action, "暂无需要 SERP 分析的关键词", metrics={"processed": 0})
    serp, strategy = services.run_serp_with_strategy(db, keyword)
    ok, reason = services.serp_admissibility(serp)
    keyword.status = "action" if ok else "watch"
    db.merge(keyword)
    output = _ok(
        action,
        f"关键词 SERP 分析完成：{keyword.query}",
        metrics={"serp_results": len(serp), "admissible": 1 if ok else 0},
        raw_result={"keyword_id": keyword.id, "keyword": keyword.query, "strategy": strategy, "admissible": ok, "reason": reason},
        inputRefs=[_target_ref(db, "keyword", str(keyword.id))],
        nextActions=[{"action_type": "opportunity.generate", "target_type": "keyword", "target_id": str(keyword.id)}] if ok else [],
    )
    source_run = _record_source_run(db, "serp", "keyword.serp_analysis", action, output, source_role="keyword")
    output["source_run_id"] = source_run.id
    return output


def _normalized_score(value: float | int | None) -> float:
    score = float(value or 0.0)
    if 0 < score <= 1:
        score *= 100
    return round(max(0.0, min(100.0, score)), 1)


def _keyword_score_components(db: Session, keyword: models.Keyword) -> dict[str, Any]:
    existing = _normalized_score(keyword.score)
    serp_rows = db.query(models.SerpResult).filter_by(keyword_id=keyword.id).order_by(models.SerpResult.rank.asc()).all()
    cards = db.query(models.OpportunityCard).filter_by(keyword_id=keyword.id).all()
    source = (keyword.source or "").lower()
    demand_score = existing
    if serp_rows:
        relevant = sum(1 for row in serp_rows[:10] if "query_mismatch" not in (row.gap_tags or ""))
        commercial = sum(1 for row in serp_rows[:10] if any(token in f"{row.title} {row.snippet}".lower() for token in ["software", "tool", "template", "calculator", "pricing", "platform", "service"]))
        demand_score = round(max(demand_score, min(100.0, 35 + relevant * 5 + commercial * 4)), 1)
    trend_score = 80.0 if any(token in source for token in ["hot", "trend", "radar", "hn", "github", "product_hunt", "steam", "arxiv"]) else 35.0
    if "sitemap" in source or "changelog" in source or "pricing" in source:
        trend_score = max(trend_score, 55.0)
    if serp_rows:
        avg_gap = sum(float(row.weakness_score or 0.0) for row in serp_rows[:10]) / max(1, min(10, len(serp_rows)))
        trend_score = max(trend_score, _normalized_score(avg_gap))
    total_score = round(demand_score * 0.65 + trend_score * 0.35, 1)
    quality = "通过" if total_score >= 70 else "观察" if total_score >= 40 else "拒绝"
    return {
        "demand_score": demand_score,
        "trend_score": round(trend_score, 1),
        "total_score": total_score,
        "serp_results": len(serp_rows),
        "opportunities": len(cards),
        "quality_status": quality,
        "formula": "总评分 = 需求分 * 65% + 趋势分 * 35%",
    }


def _keyword_rescore(db: Session, action: dict[str, Any]) -> ExecutionResult:
    payload = action.get("payload") or {}
    target_id = str(action.get("target_id") or "")
    if target_id == "all":
        try:
            limit = int(payload.get("limit") or 50)
        except Exception:
            limit = 50
        rows = db.query(models.Keyword).order_by(models.Keyword.created_at.desc()).limit(max(1, min(200, limit))).all()
    else:
        keyword = db.get(models.Keyword, int(target_id)) if target_id.isdigit() else None
        rows = [keyword] if keyword else []
    if not rows:
        return _failed(action, "关键词重评分失败", "keyword_not_found", retryable=False)
    updated: list[dict[str, Any]] = []
    next_actions: list[dict[str, Any]] = []
    for keyword in rows:
        if not keyword:
            continue
        previous = _normalized_score(keyword.score)
        components = _keyword_score_components(db, keyword)
        keyword.score = components["total_score"]
        db.merge(keyword)
        updated.append({"id": keyword.id, "query": keyword.query, "previous_score": previous, **components})
        has_serp = components["serp_results"] > 0
        if not has_serp:
            next_actions.append({"action_type": "keyword.serp_analysis", "target_type": "keyword", "target_id": str(keyword.id), "reason": "keyword_rescore_requires_serp"})
    db.commit()
    output = _ok(
        action,
        f"关键词已按统一评分规则重算：{len(updated)} 个",
        metrics={"keywords_rescored": len(updated), "actions_created": len(next_actions)},
        raw_result={"keywords": updated},
        inputRefs=[_target_ref(db, "keyword", str(row["id"])) for row in updated[:20]],
        nextActions=next_actions[:100],
    )
    source_run = _record_source_run(db, "keyword_score", "keyword.rescore", action, output, source_role="keyword")
    output["source_run_id"] = source_run.id
    return output


def _opportunity_generate(db: Session, action: dict[str, Any]) -> ExecutionResult:
    target_id = str(action.get("target_id") or "")
    keyword = db.get(models.Keyword, int(target_id)) if target_id.isdigit() else None
    if not keyword:
        return _failed(action, "机会生成失败", "keyword_not_found", retryable=False)
    card = services.make_card(db, keyword)
    output = _ok(
        action,
        f"机会已生成：{keyword.query}",
        generatedOpportunities=[{"id": card.id, "keyword_id": keyword.id, "title": card.title}],
        metrics={"cards_generated": 1},
        inputRefs=[_target_ref(db, "keyword", str(keyword.id))],
        raw_result={"keyword_id": keyword.id, "card_id": card.id, "verdict": card.verdict, "score": card.score},
    )
    source_run = _record_source_run(db, "opportunity", "opportunity.generate", action, output, source_role="opportunity")
    output["source_run_id"] = source_run.id
    return output


def _opportunity_rescore(db: Session, action: dict[str, Any]) -> ExecutionResult:
    target_id = str(action.get("target_id") or "")
    card = db.get(models.OpportunityCard, int(target_id)) if target_id.isdigit() else None
    if not card:
        return _failed(action, "机会重评分失败", "opportunity_card_not_found", retryable=False)
    previous = float(card.score or 0)
    keyword = db.get(models.Keyword, card.keyword_id) if card.keyword_id else None
    serp_count = db.query(models.SerpResult).filter_by(keyword_id=keyword.id).count() if keyword else 0
    evidence_count = db.query(models.EvidenceLink).filter_by(target_type="opportunity_card", target_id=str(card.id)).count()
    new_score = min(100.0, max(previous, 50.0 + min(serp_count, 10) * 3.0 + min(evidence_count, 10) * 2.0))
    card.score = new_score
    db.merge(card)
    output = _ok(
        action,
        f"机会已重新评分：{card.title}",
        metrics={"previous_score": previous, "new_score": new_score, "serp_results": serp_count, "evidence": evidence_count},
        raw_result={"opportunity_card_id": card.id, "keyword": keyword.query if keyword else ""},
    )
    source_run = _record_source_run(db, "opportunity", "opportunity.rescore", action, output, source_role="opportunity")
    output["source_run_id"] = source_run.id
    return output


def _evidence_backfill(db: Session, action: dict[str, Any]) -> ExecutionResult:
    target_type = str(action.get("target_type") or "")
    target_id = str(action.get("target_id") or "")
    if target_type == "evidence_task" and target_id == "manual":
        output = _ok(
            action,
            "补证据动作已进入统一队列；请在具体线索、关键词或机会对象上触发补证据以关联服务对象",
            metrics={"evidence_created": 0},
            generatedEvidence=[],
            inputRefs=[],
        )
        source_run = _record_source_run(db, "evidence", "evidence.backfill", action, output, source_role="evidence")
        output["source_run_id"] = source_run.id
        return output
    generated = _create_target_snapshot_evidence(db, target_type, target_id, created_by=str(action.get("source") or "system"))
    if not generated:
        output = _failed(
            action,
            "补证据未找到可关联对象",
            f"target_not_found_or_no_evidence_source:{target_type}:{target_id}",
            retryable=False,
            inputRefs=[_target_ref(db, target_type, target_id)],
        )
    else:
        output = _ok(
            action,
            f"补证据已完成：新增或关联 {len(generated)} 条客观证据",
            metrics={"evidence_created": len(generated)},
            generatedEvidence=generated,
            inputRefs=[_target_ref(db, target_type, target_id)],
            nextActions=[],
            target={"type": target_type, "id": target_id},
        )
    source_run = _record_source_run(db, "evidence", "evidence.backfill", action, output, source_role="evidence")
    output["source_run_id"] = source_run.id
    return output


def _generic_ack(db: Session, action: dict[str, Any]) -> ExecutionResult:
    output = _ok(
        action,
        "动作已记录到统一自动化框架",
        metrics={"actions_created": 0},
        inputRefs=[_target_ref(db, str(action.get("target_type") or ""), str(action.get("target_id") or ""))],
    )
    source_run = _record_source_run(db, "action", str(action.get("action_type") or "action"), action, output)
    output["source_run_id"] = source_run.id
    return output


def _watch_run(db: Session, action: dict[str, Any]) -> ExecutionResult:
    target_id = str(action.get("target_id") or "")
    if target_id == "all":
        now = datetime.utcnow()
        rows = (
            db.query(models.WatchTarget)
            .filter(models.WatchTarget.status == "active")
            .order_by(models.WatchTarget.priority.desc(), models.WatchTarget.updated_at.asc())
            .limit(50)
            .all()
        )
        for target in rows:
            target.last_run_at = now
            target.next_due_at = now + timedelta(hours=6)
            target.updated_at = now
            db.merge(target)
        output = _ok(action, f"已验证 {len(rows)} 个监控对象", metrics={"watch_targets": len(rows)})
        source_run = _record_source_run(db, "watch", "watch.verify", action, output, source_role="evidence")
        output["source_run_id"] = source_run.id
        return output
    target = db.get(models.WatchTarget, int(target_id)) if target_id.isdigit() else None
    if not target:
        return _failed(action, "监控对象不存在", "watch_target_not_found", retryable=False)
    now = datetime.utcnow()
    target.last_run_at = now
    target.next_due_at = now + timedelta(hours=6)
    target.updated_at = now
    db.merge(target)
    evidence = []
    generated_clues: list[dict[str, Any]] = []
    if target.source_url:
        item = evidence_system.create_evidence_item(
            db,
            source_type=target.target_type,
            source_name=target.source_name or "watch_target",
            url=target.source_url,
            title=target.target_key,
            summary=f"监控对象 {target.target_key} 已在统一周期中检查。",
            raw_json={"watch_target_id": target.id, "status": target.status},
            confidence=0.4,
        )
        link = evidence_system.link_evidence(db, item.id, "watch_target", target.id, "monitor_snapshot", "监控周期检查记录")
        evidence.append({"id": item.id, "link_id": link.id, "source_type": item.source_type, "title": item.title, "url": item.url})
    try:
        context = json.loads(target.raw_context_json or "{}")
    except Exception:
        context = {}
    clue_values = context.get("generatedClues") or context.get("discovered_terms") or context.get("keywords") or []
    if isinstance(clue_values, str):
        clue_values = [clue_values]
    if isinstance(clue_values, list):
        for value in clue_values[:50]:
            text = str(value.get("text") if isinstance(value, dict) else value).strip()
            if not text:
                continue
            existing = db.query(models.CandidateKeyword).filter_by(keyword=text, source=target.target_type or "watch", source_url=target.source_url or "").first()
            if not existing:
                existing = models.CandidateKeyword(
                    keyword=text,
                    source=target.target_type or "watch",
                    source_url=target.source_url or "",
                    source_domain=target.source_name or "",
                    method="监控回流",
                    evidence_json=_json_dumps({"inputRef": {"type": "watch_target", "id": target.id, "label": target.target_key}}),
                    score=0.5,
                    status="new",
                )
                db.add(existing)
                db.flush()
            generated_clues.append({"id": existing.id, "text": existing.keyword, "keyword": existing.keyword, "source_model": existing.source, "inputRef": {"type": "watch_target", "id": target.id, "label": target.target_key}})
    db.commit()
    output = _ok(
        action,
        f"监控对象已调度：{target.target_key}",
        metrics={"watch_targets": 1, "evidence_created": len(evidence), "generated_clues": len(generated_clues)},
        generatedEvidence=evidence,
        generatedClues=generated_clues,
        inputRefs=[_target_ref(db, "watch_target", str(target.id))],
        nextActions=[{"action_type": "clue.score", "target_type": "clue_pool", "target_id": "all", "reason": "watch_generated_clues"}] if generated_clues else [],
    )
    source_run = _record_source_run(db, target.target_type or "watch", "watch.run", action, output, source_role="evidence")
    output["source_run_id"] = source_run.id
    return output


def _collector_targets_refresh(db: Session, action: dict[str, Any]) -> ExecutionResult:
    result = collectors.refresh_collector_targets_from_cards(db)
    output = _ok(
        action,
        "已从机会判断更新搜索条件",
        metrics={
            "keyword_targets": int(result.get("keyword_targets") or 0),
            "domain_targets": int(result.get("domain_targets") or 0),
        },
        raw_result=result,
        inputRefs=[],
    )
    source_run = _record_source_run(db, "collector_targets", "collector.targets.refresh", action, output, source_role="demand")
    output["source_run_id"] = source_run.id
    return output


def _collector_targets_health(db: Session, action: dict[str, Any]) -> ExecutionResult:
    result = collectors.apply_collector_target_health(db)
    output = _ok(
        action,
        "已整理搜索条件健康状态",
        metrics={
            "cooled": int(result.get("cooled") or 0),
            "promoted": int(result.get("promoted") or 0),
        },
        raw_result=result,
        inputRefs=[],
    )
    source_run = _record_source_run(db, "collector_targets", "collector.targets.health", action, output, source_role="demand")
    output["source_run_id"] = source_run.id
    return output


def _candidate_entry_route(db: Session, action: dict[str, Any]) -> ExecutionResult:
    entry = db.get(models.CandidateEntry, int(action.get("target_id") or 0))
    if not entry:
        return _failed(action, "线索入口不存在", "candidate_entry_not_found", retryable=False)
    now = datetime.utcnow()
    generated_clues: list[dict[str, Any]] = []
    if entry.entry_type in {"search_keyword", "keyword", "demand_keyword", "trend_keyword"}:
        existing = db.query(models.CandidateKeyword).filter_by(keyword=entry.name, source=entry.source or "candidate_entry", source_url=entry.source_url or "").first()
        if not existing:
            existing = models.CandidateKeyword(
                keyword=entry.name,
                source=entry.source or "candidate_entry",
                source_url=entry.source_url or "",
                source_domain="",
                method="入口池转线索",
                evidence_json=_json_dumps({"inputRef": {"type": "candidate_entry", "id": entry.id, "label": entry.name, "source": entry.source}}),
                score=max(0.1, min(1.0, float(entry.priority or 0.0) / 100.0)),
                status="new",
            )
            db.add(existing)
            db.flush()
        generated_clues.append({"id": existing.id, "text": existing.keyword, "keyword": existing.keyword, "source_model": existing.source, "inputRef": {"type": "candidate_entry", "id": entry.id, "label": entry.name, "source": entry.source}})
    entry.next_due_at = now + timedelta(hours=6)
    entry.updated_at = now
    if entry.status == "new":
        entry.status = "needs_evidence"
    db.merge(entry)
    output = _ok(
        action,
        f"线索入口已进入自动推进队列：{entry.name}",
        metrics={"candidate_entries": 1, "generated_clues": len(generated_clues)},
        generatedClues=generated_clues,
        inputRefs=[{"type": "candidate_entry", "id": entry.id, "label": entry.name, "source": entry.source}],
        nextActions=[{"action_type": "clue.score", "target_type": "clue_pool", "target_id": "all", "reason": "candidate_entry_generated_clue"}] if generated_clues else [],
    )
    source_run = _record_source_run(db, entry.source or "candidate_entry", str(action.get("action_type") or "candidate_entry.route"), action, output, source_role=entry.source_role or "demand")
    output["source_run_id"] = source_run.id
    return output


EXECUTORS: dict[str, Executor] = {
    "legacy.daily_run": _legacy_daily,
    "automation.daily_run": _legacy_daily,
    "four_find.run": _four_find_run,
    "clue_model.run": _clue_model_run,
    "collector.run": _clue_model_run,
    "clue.score": _clue_score,
    "score_demand_keyword": _candidate_entry_route,
    "score_trend_entity": _candidate_entry_route,
    "entry.push": _candidate_entry_route,
    "create_evidence_task": _evidence_backfill,
    "evidence.backfill": _evidence_backfill,
    "evidence.collect": _evidence_backfill,
    "keyword.collect_evidence": _evidence_backfill,
    "clue.collect_evidence": _evidence_backfill,
    "opportunity.collect_evidence": _evidence_backfill,
    "keyword.rescore": _keyword_rescore,
    "clue.rescore": _clue_score,
    "keyword.serp_analysis": _keyword_serp_analysis,
    "opportunity.generate": _opportunity_generate,
    "opportunity.rescore": _opportunity_rescore,
    "watch.run": _watch_run,
    "run_watch_target": _watch_run,
    "watch.verify": _watch_run,
    "collector.targets.refresh": _collector_targets_refresh,
    "collector.targets.health": _collector_targets_health,
    "repair.action": _generic_ack,
    "keyword.repair": _generic_ack,
    "clue.restore": _generic_ack,
    "clue.promote_keyword": _clue_score,
    "opportunity.push_progress": _generic_ack,
    "progress.update_prd": _generic_ack,
    "progress.revalidate": _generic_ack,
    "verify": _generic_ack,
    "recalculate": _generic_ack,
}


def execute_registered_action(db: Session, action: dict[str, Any], request: models.ActionRequest | None = None) -> ExecutionResult:
    action_type = str(action.get("action_type") or "").strip()
    target_type = str(action.get("target_type") or "")
    target_id = str(action.get("target_id") or "")
    executor = EXECUTORS.get(action_type)
    if not executor:
        result = _failed(action, "没有找到对应执行器", f"executor_not_found:{action_type}", retryable=False)
    else:
        try:
            result = executor(db, action)
        except Exception as exc:
            result = _failed(action, "执行器运行失败", str(exc)[:500], retryable=True)

    if request:
        now = datetime.utcnow()
        request.status = result.get("status") or ("success" if result.get("ok") else "failed")
        if not request.started_at:
            request.started_at = now
        request.finished_at = now
        request.executed_at = now
        request.result_json = _json_dumps(result)
        if result.get("ok"):
            request.error_json = "{}"
        else:
            request.error_json = _json_dumps({"errors": result.get("errors") or [], "summary": result.get("summary") or ""})
        db.merge(request)
        _event(
            db,
            request.id,
            request.status,
            target_type,
            target_id,
            str(result.get("summary") or action_type),
            result,
        )
    return result
