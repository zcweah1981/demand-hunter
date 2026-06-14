import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas, services
from app.api.v1.endpoints import actions as actions_endpoint
from app.api.v1.endpoints import automation_cycle as automation_cycle_endpoint
from app.api.v1.endpoints import cards as cards_endpoint
from app.api.v1.endpoints import collectors as collectors_endpoint
from app.api.v1.endpoints import discovery as discovery_endpoint
from app.api.v1.endpoints import keywords as keywords_endpoint
from app.automation_cycle import collect_due_actions, run_automation_cycle
from app.database import Base


class AutomationCycleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_collects_due_actions_from_multiple_objects(self):
        now = datetime.utcnow()
        with self.Session() as db:
            db.add(models.Setting(key="COLLECTOR_AUTO_ENABLED", value="false", secret=False))
            db.add(
                models.CandidateEntry(
                    entry_type="search_keyword",
                    name="shopify tax calculator",
                    source="test",
                    source_role="demand",
                    priority=50,
                    next_due_at=now - timedelta(minutes=1),
                )
            )
            db.add(
                models.WatchTarget(
                    target_type="pricing_page",
                    target_key="example.com/pricing",
                    priority=80,
                    next_due_at=now - timedelta(minutes=1),
                )
            )
            db.add(
                models.ActionRequest(
                    action_type="recalculate",
                    target_type="keyword",
                    target_id="1",
                    risk_level="low",
                    status="pending",
                )
            )
            db.commit()

            actions = collect_due_actions(db, now=now)

            self.assertEqual({a["source"] for a in actions}, {"candidate_entry", "watch_target", "action_request"})
            self.assertEqual(actions[0]["source"], "watch_target")

    def test_run_cycle_writes_run_history(self):
        now = datetime.utcnow()
        with self.Session() as db:
            db.add(models.Setting(key="COLLECTOR_AUTO_ENABLED", value="false", secret=False))
            db.add(
                models.CandidateEntry(
                    entry_type="search_keyword",
                    name="invoice automation tool",
                    source="test",
                    source_role="demand",
                    priority=40,
                    next_due_at=now - timedelta(minutes=1),
                )
            )
            db.commit()

            result = run_automation_cycle(db, now=now, max_seconds=10)

            self.assertTrue(result["ok"])
            self.assertGreaterEqual(result["executed"], 1)
            history = db.query(models.RunHistory).filter_by(kind="automation_cycle").first()
            self.assertIsNotNone(history)

    def test_candidate_entry_cycle_writes_source_run(self):
        now = datetime.utcnow()
        with self.Session() as db:
            db.add(models.Setting(key="COLLECTOR_AUTO_ENABLED", value="false", secret=False))
            entry = models.CandidateEntry(
                entry_type="search_keyword",
                name="invoice automation tool",
                source="manual_seed",
                source_role="demand",
                priority=40,
                next_due_at=now - timedelta(minutes=1),
            )
            db.add(entry)
            db.commit()

            result = run_automation_cycle(db, now=now, max_seconds=10)

            self.assertTrue(result["ok"])
            source_run = db.query(models.SourceRun).filter_by(target_type="candidate_entry", target_id=str(entry.id)).first()
            self.assertIsNotNone(source_run)
            self.assertEqual(source_run.source, "manual_seed")
            self.assertEqual(source_run.status, "ok")
            clue = db.query(models.CandidateKeyword).filter_by(keyword="invoice automation tool").first()
            self.assertIsNotNone(clue)
            self.assertEqual(clue.method, "入口池转线索")

    def test_watch_run_generated_terms_flow_back_to_clue_pool(self):
        now = datetime.utcnow()
        with self.Session() as db:
            db.add(models.Setting(key="COLLECTOR_AUTO_ENABLED", value="false", secret=False))
            watch = models.WatchTarget(
                target_type="changelog",
                target_key="example changelog",
                source_url="https://example.com/changelog",
                status="active",
                priority=70,
                next_due_at=now - timedelta(minutes=1),
                raw_context_json=json.dumps({"discovered_terms": ["invoice workflow automation"]}, ensure_ascii=False),
            )
            db.add(watch)
            db.commit()

            result = run_automation_cycle(db, now=now, max_seconds=10)

            self.assertTrue(result["ok"])
            clue = db.query(models.CandidateKeyword).filter_by(keyword="invoice workflow automation", source="changelog").first()
            self.assertIsNotNone(clue)
            self.assertEqual(clue.method, "监控回流")
            follow_up = db.query(models.ActionRequest).filter_by(action_type="clue.score", target_type="clue_pool", target_id="all").first()
            self.assertIsNotNone(follow_up)

    def test_keyword_rescore_uses_unified_zero_to_hundred_score(self):
        with self.Session() as db:
            keyword = models.Keyword(query="invoice automation", source="collector:hot_topic", status="new", score=0.82)
            db.add(keyword)
            db.commit()
            db.refresh(keyword)
            db.add(
                models.ActionRequest(
                    action_type="keyword.rescore",
                    target_type="keyword",
                    target_id=str(keyword.id),
                    risk_level="low",
                    status="pending",
                )
            )
            db.commit()

            result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            db.refresh(keyword)
            self.assertGreaterEqual(keyword.score, 0)
            self.assertLessEqual(keyword.score, 100)
            self.assertNotEqual(keyword.score, 8010.0)
            request = db.query(models.ActionRequest).filter_by(action_type="keyword.rescore").first()
            payload = json.loads(request.result_json or "{}")
            self.assertEqual(payload["raw_result"]["keywords"][0]["formula"], "总评分 = 需求分 * 65% + 趋势分 * 35%")
            self.assertIsNotNone(
                db.query(models.ActionRequest)
                .filter_by(action_type="keyword.serp_analysis", target_type="keyword", target_id=str(keyword.id))
                .first()
            )

    def test_cycle_enqueues_executor_next_actions(self):
        with self.Session() as db:
            candidate = models.CandidateKeyword(
                keyword="vendor compliance tracker",
                source="suggest",
                method="词找词",
                score=0.9,
                status="new",
            )
            db.add(candidate)
            db.add(
                models.ActionRequest(
                    action_type="clue.score",
                    target_type="clue_pool",
                    target_id="all",
                    risk_level="low",
                    status="pending",
                )
            )
            db.commit()

            result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            keyword = db.query(models.Keyword).filter_by(query="vendor compliance tracker").first()
            self.assertIsNotNone(keyword)
            follow_up = (
                db.query(models.ActionRequest)
                .filter_by(action_type="keyword.serp_analysis", target_type="keyword", target_id=str(keyword.id))
                .first()
            )
            self.assertIsNotNone(follow_up)
            history = db.query(models.RunHistory).filter_by(kind="automation_cycle").first()
            self.assertIsNotNone(history)
            self.assertEqual(follow_up.run_id, history.id)

    def test_clue_model_executor_runs_connected_single_models(self):
        def add_candidate(db_session, keyword, source):
            row = models.CandidateKeyword(
                keyword=keyword,
                source=source,
                method="自动化测试",
                score=0.7,
                status="new",
            )
            db_session.add(row)
            db_session.commit()
            return {"ok": True, "source": source, "saved": 1, "candidates_seen": 1, "errors": []}

        cases = [
            (
                "hot_topic",
                {"model": "hot_topic", "topics": ["invoice automation"], "max_seconds": 1},
                "app.automation_executors.collectors.run_hot_topic_collector",
                lambda db_session, topics=None, max_seconds=None: add_candidate(db_session, "invoice automation 2026", "hot_topic"),
            ),
            (
                "serp_search",
                {"model": "serp_search", "roots": ["vendor compliance"], "max_seconds": 1},
                "app.automation_executors.collectors.run_advanced_search_collector",
                lambda db_session, roots, domains=None, days=30, limit_per_query=8, max_seconds=None: add_candidate(db_session, "vendor compliance checklist", "advanced_search"),
            ),
            (
                "source_radar",
                {"model": "source_radar", "seeds": ["ai agent"], "max_seconds": 1},
                "app.automation_executors.collectors.run_source_radar",
                lambda db_session, seeds, limit_per_seed=10, max_seconds=None: add_candidate(db_session, "ai agent framework", "source_radar"),
            ),
        ]

        for model, payload, patch_target, fake_runner in cases:
            with self.subTest(model=model):
                with self.Session() as db:
                    db.add(
                        models.ActionRequest(
                            action_type="clue_model.run",
                            target_type="clue_model",
                            target_id=model,
                            risk_level="low",
                            status="pending",
                            payload_json=json.dumps(payload, ensure_ascii=False),
                        )
                    )
                    db.commit()

                    with patch(patch_target, side_effect=fake_runner):
                        result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

                    self.assertTrue(result["ok"])
                    request = db.query(models.ActionRequest).filter_by(action_type="clue_model.run").first()
                    self.assertEqual(request.status, "success")
                    result_payload = json.loads(request.result_json or "{}")
                    self.assertTrue(result_payload.get("inputRefs"))
                    source_run = db.query(models.SourceRun).filter_by(run_kind="clue_model.run").first()
                    self.assertIsNotNone(source_run)
                    self.assertEqual(source_run.status, "ok")
                    self.assertGreater(db.query(models.CandidateKeyword).count(), 0)

    def test_clue_model_four_find_records_generated_keywords_and_input_refs(self):
        def fake_four_find(db_session, limit=12, seeds=None):
            keyword = models.Keyword(query="invoice automation software", source="four_find", status="new", score=72)
            db_session.add(keyword)
            db_session.commit()
            db_session.refresh(keyword)
            return [keyword]

        with self.Session() as db:
            db.add(
                models.ActionRequest(
                    action_type="clue_model.run",
                    target_type="clue_model",
                    target_id="four_find",
                    risk_level="low",
                    status="pending",
                    payload_json=json.dumps({"model": "four_find", "seeds": ["invoice automation"], "limit": 1}, ensure_ascii=False),
                )
            )
            db.commit()

            with patch("app.automation_executors.services.discover_keywords_four_find", side_effect=fake_four_find):
                result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            request = db.query(models.ActionRequest).filter_by(action_type="clue_model.run").first()
            result_payload = json.loads(request.result_json or "{}")
            self.assertEqual(request.status, "success")
            self.assertEqual(result_payload["generatedKeywords"][0]["query"], "invoice automation software")
            self.assertEqual(result_payload["inputRefs"][0]["label"], "invoice automation")

    def test_four_find_action_runs_through_unified_cycle(self):
        def fake_expand(db_session, seed, search_fn):
            row = models.DiscoveryExpansion(
                seed_keyword=seed,
                expanded_keyword=f"{seed} template",
                expansion_type="business_modifier",
                score=0.8,
                status="new",
            )
            db_session.add(row)
            db_session.commit()
            db_session.refresh(row)
            return [row]

        with self.Session() as db:
            db.add(
                models.ActionRequest(
                    action_type="four_find.run",
                    target_type="four_find",
                    target_id="expand",
                    risk_level="low",
                    status="pending",
                    payload_json=json.dumps({"operation": "expand", "seed": "invoice automation"}, ensure_ascii=False),
                )
            )
            db.commit()

            with patch("app.automation_executors.four_find.expand_by_suggest", side_effect=fake_expand), patch(
                "app.automation_executors.four_find.expand_by_related",
                return_value=[],
            ):
                result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            request = db.query(models.ActionRequest).filter_by(action_type="four_find.run").first()
            self.assertEqual(request.status, "success")
            result_payload = json.loads(request.result_json or "{}")
            self.assertEqual(result_payload["generatedClues"][0]["keyword"], "invoice automation template")
            self.assertEqual(result_payload["inputRefs"][0]["label"], "invoice automation")
            source_run = db.query(models.SourceRun).filter_by(run_kind="four_find.expand").first()
            self.assertIsNotNone(source_run)

    def test_four_find_import_enqueues_keyword_serp_action(self):
        with self.Session() as db:
            expansion = models.DiscoveryExpansion(
                seed_keyword="invoice automation",
                expanded_keyword="invoice automation template",
                expansion_type="business_modifier",
                score=0.8,
                status="new",
            )
            db.add(expansion)
            db.commit()
            db.refresh(expansion)
            db.add(
                models.ActionRequest(
                    action_type="four_find.run",
                    target_type="four_find",
                    target_id=str(expansion.id),
                    risk_level="low",
                    status="pending",
                    payload_json=json.dumps({"operation": "import_expansion"}, ensure_ascii=False),
                )
            )
            db.commit()

            result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            keyword = db.query(models.Keyword).filter_by(query="invoice automation template").first()
            self.assertIsNotNone(keyword)
            self.assertIsNotNone(
                db.query(models.ActionRequest)
                .filter_by(action_type="keyword.serp_analysis", target_type="keyword", target_id=str(keyword.id))
                .first()
            )

    def test_collector_target_actions_run_through_unified_cycle(self):
        cases = [
            (
                "collector.targets.refresh",
                "app.automation_executors.collectors.refresh_collector_targets_from_cards",
                {"keyword_targets": 2, "domain_targets": 1},
                "collector.targets.refresh",
                "keyword_targets",
                2,
            ),
            (
                "collector.targets.health",
                "app.automation_executors.collectors.apply_collector_target_health",
                {"cooled": 3, "promoted": 4},
                "collector.targets.health",
                "cooled",
                3,
            ),
        ]

        for action_type, patch_target, return_value, run_kind, metric_key, metric_value in cases:
            with self.subTest(action_type=action_type):
                with self.Session() as db:
                    db.add(
                        models.ActionRequest(
                            action_type=action_type,
                            target_type="collector_targets",
                            target_id="all",
                            risk_level="low",
                            status="pending",
                        )
                    )
                    db.commit()

                    with patch(patch_target, return_value=return_value) as mocked:
                        result = run_automation_cycle(
                            db,
                            max_seconds=10,
                            run_legacy_daily=False,
                            include_default_actions=False,
                        )

                    self.assertTrue(result["ok"])
                    self.assertEqual(mocked.call_count, 1)
                    request = db.query(models.ActionRequest).filter_by(action_type=action_type).first()
                    self.assertEqual(request.status, "success")
                    payload = json.loads(request.result_json or "{}")
                    self.assertEqual(payload["metrics"][metric_key], metric_value)
                    source_run = db.query(models.SourceRun).filter_by(run_kind=run_kind).first()
                    self.assertIsNotNone(source_run)

    def test_collect_due_actions_skips_keyword_when_serp_request_is_open(self):
        with self.Session() as db:
            keyword = models.Keyword(query="invoice automation", source="test", status="new", score=90)
            db.add(keyword)
            db.commit()
            db.refresh(keyword)
            db.add(
                models.ActionRequest(
                    action_type="keyword.serp_analysis",
                    target_type="keyword",
                    target_id=str(keyword.id),
                    risk_level="low",
                    status="pending",
                )
            )
            db.commit()

            actions = collect_due_actions(db)

            self.assertNotIn("keyword", {action["source"] for action in actions})
            self.assertIn("action_request", {action["source"] for action in actions})

    def test_cycle_consumes_serp_next_action_to_generate_opportunity(self):
        def fake_run_serp(db_session, keyword):
            serp = models.SerpResult(
                keyword_id=keyword.id,
                rank=1,
                title="Vendor compliance tracker",
                url="https://example.com/vendor-compliance",
                snippet="Example result",
                domain="example.com",
            )
            db_session.add(serp)
            db_session.commit()
            return [serp], {"provider": "test"}

        def fake_make_card(db_session, keyword):
            card = models.OpportunityCard(keyword_id=keyword.id, title=keyword.query, verdict="Action", score=88)
            db_session.add(card)
            db_session.commit()
            db_session.refresh(card)
            return card

        with self.Session() as db:
            keyword = models.Keyword(query="vendor compliance tracker", source="test", status="new", score=90)
            db.add(keyword)
            db.add(
                models.ActionRequest(
                    action_type="keyword.serp_analysis",
                    target_type="keyword",
                    target_id="1",
                    risk_level="low",
                    status="pending",
                )
            )
            db.commit()
            db.refresh(keyword)
            request = db.query(models.ActionRequest).filter_by(action_type="keyword.serp_analysis").first()
            request.target_id = str(keyword.id)
            db.merge(request)
            db.commit()

            with patch("app.automation_executors.services.run_serp_with_strategy", side_effect=fake_run_serp), patch(
                "app.automation_executors.services.serp_admissibility",
                return_value=(True, "test"),
            ), patch("app.automation_executors.services.make_card", side_effect=fake_make_card):
                result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            self.assertEqual(db.query(models.OpportunityCard).count(), 1)
            self.assertEqual(db.query(models.ActionRequest).filter_by(action_type="opportunity.generate", status="success").count(), 1)

    def test_cycle_marks_action_request_with_run_id_and_payload(self):
        with self.Session() as db:
            request = models.ActionRequest(
                action_type="recalculate",
                target_type="keyword",
                target_id="42",
                risk_level="low",
                status="pending",
                payload_json='{"reason_detail":"from test"}',
            )
            db.add(request)
            db.commit()

            result = run_automation_cycle(db, max_seconds=10, run_legacy_daily=False, include_default_actions=False)

            self.assertTrue(result["ok"])
            db.refresh(request)
            history = db.query(models.RunHistory).filter_by(kind="automation_cycle").first()
            self.assertIsNotNone(history)
            self.assertEqual(request.status, "success")
            self.assertEqual(request.run_id, history.id)
            self.assertIsNotNone(request.started_at)
            self.assertIsNotNone(request.finished_at)

    def test_default_cycle_does_not_run_legacy_daily(self):
        with self.Session() as db:
            db.add(models.Setting(key="COLLECTOR_AUTO_ENABLED", value="false", secret=False))
            db.commit()

            result = run_automation_cycle(db, max_seconds=10)

            self.assertTrue(result["ok"])
            self.assertIsNone(result["daily_run"])
            self.assertEqual(db.query(models.RunHistory).filter_by(kind="daily").count(), 0)
            history = db.query(models.RunHistory).filter_by(kind="automation_cycle").first()
            self.assertIsNotNone(history)
            self.assertEqual(history.status, "ok")

    def test_auto_status_uses_automation_cycle_as_schedule_basis(self):
        now = datetime.utcnow()
        with self.Session() as db:
            db.add(models.Setting(key="AUTO_RUN_ENABLED", value="true", secret=False))
            db.add(models.Setting(key="AUTO_RUN_INTERVAL_MINUTES", value="360", secret=False))
            db.add(
                models.RunHistory(
                    kind="daily",
                    status="ok",
                    summary='{"trigger":"auto_scheduled"}',
                    started_at=now - timedelta(hours=1),
                    finished_at=now - timedelta(hours=1),
                )
            )
            cycle = models.RunHistory(
                kind="automation_cycle",
                status="ok",
                summary='{"stage":"finished","processed":1}',
                started_at=now - timedelta(hours=3),
                finished_at=now - timedelta(hours=3),
            )
            db.add(cycle)
            db.commit()

            status = services.auto_status(db)

            self.assertEqual(status["schedule_basis"], "last_automation_cycle")
            self.assertEqual(status["last_run"]["kind"], "automation_cycle")
            self.assertEqual(status["last_run"]["id"], cycle.id)

    def test_action_detail_parses_runtime_json(self):
        with self.Session() as db:
            row = models.ActionRequest(
                action_type="keyword.serp_analysis",
                target_type="keyword",
                target_id="7",
                risk_level="low",
                status="failed",
                payload_json=json.dumps({"keyword": "invoice automation"}),
                result_json=json.dumps({"ok": False, "generatedClues": []}),
                error_json=json.dumps({"message": "timeout", "retryable": True}),
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            data = actions_endpoint.action_detail(row.id, _=True, db=db)

            self.assertEqual(data["payload_json"]["keyword"], "invoice automation")
            self.assertFalse(data["result_json"]["ok"])
            self.assertTrue(data["error_json"]["retryable"])

    def test_automation_run_detail_returns_summary_and_actions(self):
        now = datetime.utcnow()
        with self.Session() as db:
            run = models.RunHistory(
                kind="automation_cycle",
                status="ok",
                summary=json.dumps({"stage": "finished", "executed": 1}),
                started_at=now,
                finished_at=now,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            db.add(
                models.ActionRequest(
                    action_type="clue.score",
                    target_type="clue_pool",
                    target_id="all",
                    risk_level="low",
                    status="success",
                    run_id=run.id,
                    result_json=json.dumps({"ok": True, "summary": "scored"}),
                )
            )
            db.commit()

            data = automation_cycle_endpoint.automation_run_detail(run.id, _=True, db=db)

            self.assertEqual(data["summary"]["stage"], "finished")
            self.assertEqual(len(data["actions"]), 1)
            self.assertTrue(data["actions"][0]["result_json"]["ok"])

    def test_automation_runs_exposes_running_progress_summary(self):
        now = datetime.utcnow()
        with self.Session() as db:
            db.add(
                models.RunHistory(
                    kind="automation_cycle",
                    status="running",
                    summary=json.dumps(
                        {
                            "stage": "running",
                            "actions_collected": 5,
                            "processed": 2,
                            "executed": 2,
                            "failed": 0,
                        },
                        ensure_ascii=False,
                    ),
                    started_at=now,
                )
            )
            db.commit()

            rows = automation_cycle_endpoint.automation_runs(_=True, db=db)

            self.assertEqual(rows[0]["status"], "running")
            self.assertEqual(rows[0]["summary"]["stage"], "running")
            self.assertEqual(rows[0]["summary"]["processed"], 2)
            self.assertEqual(rows[0]["summary"]["actions_collected"], 5)

    def test_automation_run_api_honors_include_default_actions_flag(self):
        with self.Session() as db:
            with patch(
                "app.api.v1.endpoints.automation_cycle.automation_cycle.run_automation_cycle",
                return_value={"ok": True, "summary": {"executed": 0}},
            ) as mocked:
                data = automation_cycle_endpoint.automation_run(
                    {"background": False, "include_default_actions": False},
                    _=True,
                    db=db,
                )

            self.assertTrue(data["ok"])
            self.assertFalse(mocked.call_args.kwargs["include_default_actions"])

    def test_background_automation_run_returns_trackable_run_id(self):
        class FakeThread:
            def __init__(self, target, daemon=False):
                self.target = target
                self.daemon = daemon

            def start(self):
                return None

        with self.Session() as db:
            with patch("app.api.v1.endpoints.automation_cycle.threading.Thread", FakeThread):
                data = automation_cycle_endpoint.automation_run({"background": True}, _=True, db=db)
            try:
                self.assertTrue(data["started"])
                self.assertTrue(data["run_id"])
                self.assertEqual(data["status_url"], f"/api/automation-cycle/runs/{data['run_id']}")
                row = db.get(models.RunHistory, data["run_id"])
                self.assertIsNotNone(row)
                self.assertEqual(row.status, "running")
                summary = json.loads(row.summary or "{}")
                self.assertEqual(summary["stage"], "queued")
            finally:
                if automation_cycle_endpoint.RUN_LOCK.locked():
                    automation_cycle_endpoint.RUN_LOCK.release()

    def test_cycle_can_reuse_precreated_run_history(self):
        with self.Session() as db:
            db.add(models.Setting(key="COLLECTOR_AUTO_ENABLED", value="false", secret=False))
            run = models.RunHistory(kind="automation_cycle", status="running", summary="{}", started_at=datetime.utcnow())
            db.add(run)
            db.commit()
            db.refresh(run)

            result = run_automation_cycle(db, max_seconds=10, run_id=run.id)

            self.assertTrue(result["ok"])
            rows = db.query(models.RunHistory).filter_by(kind="automation_cycle").all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].id, run.id)
            self.assertEqual(rows[0].status, "ok")

    def test_keyword_serp_legacy_endpoint_uses_action_executor(self):
        def fake_run_serp(db_session, keyword):
            serp = models.SerpResult(
                keyword_id=keyword.id,
                rank=1,
                title="Invoice automation tool",
                url="https://example.com/invoice",
                snippet="Tool result",
                domain="example.com",
            )
            db_session.add(serp)
            db_session.commit()
            return [serp], {"provider": "test"}

        with self.Session() as db:
            keyword = models.Keyword(query="invoice automation", source="test", status="new", score=80)
            db.add(keyword)
            db.commit()
            db.refresh(keyword)

            with patch("app.automation_executors.services.run_serp_with_strategy", side_effect=fake_run_serp), patch(
                "app.automation_executors.services.serp_admissibility",
                return_value=(True, "ok"),
            ):
                data = keywords_endpoint.run_serp(keyword.id, _=True, db=db)

            self.assertTrue(data["ok"])
            self.assertTrue(data["request_id"])
            self.assertTrue(data["run_id"])
            self.assertEqual(len(data["serp"]), 1)
            request = db.get(models.ActionRequest, data["request_id"])
            self.assertEqual(request.action_type, "keyword.serp_analysis")
            self.assertEqual(request.status, "success")
            run = db.get(models.RunHistory, data["run_id"])
            self.assertEqual(run.kind, "manual_action")

    def test_card_generate_legacy_endpoint_uses_action_executor(self):
        def fake_make_card(db_session, keyword):
            card = models.OpportunityCard(keyword_id=keyword.id, title=f"{keyword.query} opportunity", verdict="Action", score=90)
            db_session.add(card)
            db_session.commit()
            db_session.refresh(card)
            return card

        with self.Session() as db:
            keyword = models.Keyword(query="invoice automation", source="test", status="action", score=88)
            db.add(keyword)
            db.commit()
            db.refresh(keyword)

            with patch("app.automation_executors.services.make_card", side_effect=fake_make_card):
                data = cards_endpoint.generate_card(keyword.id, _=True, db=db)

            self.assertTrue(data["ok"])
            self.assertTrue(data["request_id"])
            self.assertTrue(data["run_id"])
            self.assertEqual(data["card"]["title"], "invoice automation opportunity")
            request = db.get(models.ActionRequest, data["request_id"])
            self.assertEqual(request.action_type, "opportunity.generate")
            self.assertEqual(request.status, "success")
            run = db.get(models.RunHistory, data["run_id"])
            self.assertEqual(run.kind, "manual_action")

    def test_collector_legacy_run_endpoint_uses_action_executor(self):
        def fake_suggest(db_session, seeds):
            row = models.CandidateKeyword(keyword="invoice automation", source="suggest", method="suggest", score=0.82)
            db_session.add(row)
            db_session.commit()
            return {"ok": True, "source": "suggest", "seen": len(seeds), "created": 1, "errors": []}

        with self.Session() as db:
            payload = schemas.CollectorSuggestIn(seeds=["invoice"])
            with patch("app.automation_executors.collectors.run_suggest_collector", side_effect=fake_suggest):
                data = collectors_endpoint.suggest_run(payload, _=True, db=db)

            self.assertTrue(data["ok"])
            self.assertTrue(data["request_id"])
            self.assertTrue(data["run_id"])
            request = db.get(models.ActionRequest, data["request_id"])
            self.assertEqual(request.action_type, "clue_model.run")
            self.assertEqual(request.target_id, "suggest")
            self.assertEqual(request.status, "success")
            run = db.get(models.RunHistory, data["run_id"])
            self.assertEqual(run.kind, "manual_action")
            result = json.loads(request.result_json)
            self.assertEqual(result["generatedClues"][0]["keyword"], "invoice automation")

    def test_discovery_legacy_endpoint_uses_four_find_executor(self):
        def fake_expand(db_session, seed, search):
            row = models.DiscoveryExpansion(
                seed_keyword=seed,
                expanded_keyword="invoice automation template",
                expansion_type="suggest",
            )
            db_session.add(row)
            db_session.commit()
            return [row]

        with self.Session() as db:
            payload = schemas.DiscoverySeedIn(seed="invoice automation")
            with patch("app.automation_executors.four_find.expand_by_suggest", side_effect=fake_expand), patch(
                "app.automation_executors.four_find.expand_by_related",
                return_value=[],
            ):
                data = discovery_endpoint.discovery_expand(payload, _=True, db=db)

            self.assertTrue(data["ok"])
            self.assertTrue(data["request_id"])
            self.assertTrue(data["run_id"])
            request = db.get(models.ActionRequest, data["request_id"])
            self.assertEqual(request.action_type, "four_find.run")
            self.assertEqual(request.target_id, "expand")
            self.assertEqual(request.status, "success")
            run = db.get(models.RunHistory, data["run_id"])
            self.assertEqual(run.kind, "manual_action")
            result = json.loads(request.result_json)
            self.assertEqual(result["generatedClues"][0]["keyword"], "invoice automation template")


if __name__ == "__main__":
    unittest.main()
