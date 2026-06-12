import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app import schemas
from app.api.v1.endpoints import collectors as collector_endpoints
from app import clue_pool
from app.clue_pool import list_clues
from app.database import Base
from app.evidence_models import model_detail, model_overview, source_to_model_id
from app.evidence_system import create_evidence_item, link_evidence, timeline_for_target


class EvidenceModelTests(unittest.TestCase):
    def test_evidence_item_has_no_scoring_fields(self):
        columns = set(models.EvidenceItem.__table__.columns.keys())

        self.assertIn("url", columns)
        self.assertIn("title", columns)
        self.assertIn("summary", columns)
        self.assertIn("confidence", columns)
        self.assertNotIn("score_delta", columns)
        self.assertNotIn("verdict", columns)

    def test_evidence_link_points_to_service_target(self):
        columns = set(models.EvidenceLink.__table__.columns.keys())

        self.assertIn("evidence_id", columns)
        self.assertIn("target_type", columns)
        self.assertIn("target_id", columns)
        self.assertIn("relation_type", columns)
        self.assertIn("relation_reason", columns)


class EvidenceServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_evidence_item_dedupes_by_content_hash(self):
        with self.Session() as db:
            first = create_evidence_item(
                db,
                source_type="sitemap_monitor",
                source_name="game wiki",
                url="https://example.com/build-planner",
                title="Build Planner",
                summary="New build planner page.",
            )
            second = create_evidence_item(
                db,
                source_type="sitemap_monitor",
                source_name="game wiki",
                url="https://example.com/build-planner",
                title="Build Planner",
                summary="New build planner page.",
            )

            self.assertEqual(first.id, second.id)
            self.assertEqual(db.query(models.EvidenceItem).count(), 1)

    def test_one_evidence_can_serve_multiple_targets(self):
        with self.Session() as db:
            evidence = create_evidence_item(
                db,
                source_type="sitemap_monitor",
                source_name="game wiki",
                url="https://example.com/items",
                title="Item Database",
                summary="New item database page.",
            )

            link_evidence(db, evidence.id, "candidate_entry", "1", "derived_from", "new page")
            link_evidence(db, evidence.id, "keyword", "2", "source_signal", "keyword weight")

            self.assertEqual(db.query(models.EvidenceLink).count(), 2)

    def test_timeline_filters_by_service_target(self):
        with self.Session() as db:
            evidence = create_evidence_item(
                db,
                source_type="pricing_page",
                source_name="competitor",
                url="https://example.com/pricing",
                title="Pricing",
                summary="Competitor changed pricing.",
            )
            link_evidence(db, evidence.id, "keyword", "42", "source_signal", "pricing clue")
            link_evidence(db, evidence.id, "opportunity_card", "7", "supporting_context", "pricing clue")

            timeline = timeline_for_target(db, "keyword", "42")

            self.assertEqual(len(timeline), 1)
            self.assertEqual(timeline[0]["link"]["target_type"], "keyword")
            self.assertEqual(timeline[0]["evidence"]["title"], "Pricing")

    def test_evidence_does_not_mutate_opportunity_verdict(self):
        with self.Session() as db:
            keyword = models.Keyword(query="game build planner")
            db.add(keyword)
            db.commit()
            db.refresh(keyword)
            card = models.OpportunityCard(keyword_id=keyword.id, title="Game Build Planner", verdict="Watch")
            db.add(card)
            db.commit()
            db.refresh(card)
            evidence = create_evidence_item(
                db,
                source_type="community",
                source_name="forum",
                url="https://example.com/thread",
                title="Players need builds",
                summary="Players ask for build planning.",
            )

            link_evidence(db, evidence.id, "opportunity_card", str(card.id), "supporting_context", "community demand")
            db.refresh(card)

            self.assertEqual(card.verdict, "Watch")


class EvidenceModelLoopTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_four_find_sources_map_to_evidence_models(self):
        self.assertEqual(source_to_model_id("suggest", "词找词"), "keyword_to_keyword")
        self.assertEqual(source_to_model_id("advanced_search", "词找站"), "keyword_to_site")
        self.assertEqual(source_to_model_id("sitemap", "站找词"), "site_to_keyword")
        self.assertEqual(source_to_model_id("alternatives", "站找站"), "site_to_site")

    def test_model_overview_counts_existing_loop_outputs(self):
        with self.Session() as db:
            db.add(models.CandidateKeyword(keyword="invoice automation", source="suggest", method="词找词"))
            db.add(models.CandidateEntry(entry_type="domain", name="example.com", source="sitemap", source_role="evidence"))
            db.add(
                models.SourceRun(
                    source="sitemap",
                    source_role="evidence",
                    run_kind="site_monitor",
                    candidates_created=2,
                    evidence_created=1,
                )
            )
            db.commit()
            create_evidence_item(
                db,
                source_type="sitemap",
                source_name="example.com",
                url="https://example.com/new-tool",
                title="New tool",
                summary="New tool page appeared.",
            )

            overview = model_overview(db)
            by_id = {item["id"]: item for item in overview["items"]}

            self.assertEqual(by_id["keyword_to_keyword"]["stats"]["candidate_keywords"], 1)
            self.assertGreaterEqual(by_id["site_to_keyword"]["stats"]["entries"], 1)
            self.assertGreaterEqual(by_id["site_to_keyword"]["stats"]["evidence"], 1)
            self.assertGreaterEqual(by_id["site_to_keyword"]["stats"]["runs"], 1)

    def test_model_detail_returns_loop_objects(self):
        with self.Session() as db:
            db.add(models.CandidateKeyword(keyword="ai invoice tool", source="suggest", method="词找词"))
            db.commit()

            detail = model_detail(db, "keyword_to_keyword")

            self.assertIsNotNone(detail)
            self.assertEqual(detail["name"], "词找词")
            self.assertEqual(len(detail["candidate_keywords"]), 1)


class CluePoolTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_candidate_keyword_clue_exposes_trace_scores_and_status(self):
        with self.Session() as db:
            db.add(
                models.CandidateKeyword(
                    keyword="hermes agent",
                    source="suggest",
                    method="词找词",
                    score=0.74,
                    status="new",
                    evidence_json='{"inputRef":{"type":"keyword","value":"ai tools"},"source_run_id":12}',
                )
            )
            db.commit()

            clue = list_clues(db)["items"][0]

            self.assertEqual(clue["value"], "hermes agent")
            self.assertEqual(clue["status"], "candidate_keyword")
            self.assertEqual(clue["status_label"], "候选关键词")
            self.assertEqual(clue["source_model"], "Google Suggest")
            self.assertEqual(clue["input_ref"]["value"], "ai tools")
            self.assertEqual(clue["source_run_id"], 12)
            self.assertGreater(clue["demand_score"], 0)
            self.assertIn("需求分", clue["score_explanation"][0])
            self.assertIn("质量门", clue["next_action_reason"])
            self.assertIn(clue["assessment"]["recommendation"], {"长期关注", "短期观察", "补证后再判断", "仅保留记录", "排除"})
            self.assertTrue(clue["assessment"]["summary"])
            self.assertGreaterEqual(len(clue["quality_checks"]), 5)
            self.assertEqual(clue["quality_checks"][0]["name"], "需求明确度")
            self.assertIn("candidate_quality_score", clue["scoring"])
            self.assertIn("breakdown", clue["scoring"])
            self.assertTrue(clue["scoring"]["formula"])
            self.assertEqual(clue["lifecycle_status"], "candidate")
            self.assertEqual(clue["lifecycle_status_label"], "候选")
            self.assertEqual(clue["processing_status"], "needs_evidence")
            self.assertEqual(clue["processing_status_label"], "待补证据")
            self.assertIn(clue["quality_status"], {"pass", "observe", "reject"})
            self.assertIn("quality_status_label", clue)

    def test_historical_candidate_without_input_ref_is_explicit(self):
        with self.Session() as db:
            db.add(models.CandidateKeyword(keyword="invoice automation", source="sitemap", method="站找词", score=0.62, status="new"))
            db.commit()

            clue = list_clues(db)["items"][0]

            self.assertEqual(clue["input_ref"]["status"], "missing_historical")
            self.assertIn("历史记录", clue["input_ref"]["label"])

    def test_entry_clue_total_score_is_normalized_for_display(self):
        with self.Session() as db:
            db.add(
                models.CandidateEntry(
                    entry_type="topic",
                    name="tax calculator how the one big beautiful bill",
                    source="hot_topic",
                    source_role="collector",
                    priority=8010,
                    trend_score=80.1,
                    status="new",
                )
            )
            db.commit()

            clue = list_clues(db)["items"][0]

            self.assertLessEqual(clue["total_score"], 100)
            self.assertEqual(clue["total_score"], 28.0)
            self.assertIn("入口趋势分", clue["score_explanation"][0])
            self.assertIn("需求分待评分", clue["score_explanation"][1])

    def test_imported_candidate_links_keyword_and_opportunity(self):
        with self.Session() as db:
            keyword = models.Keyword(query="vendor compliance tracker", source="collector:suggest", score=0.8, status="new")
            db.add(keyword)
            db.commit()
            db.refresh(keyword)
            card = models.OpportunityCard(keyword_id=keyword.id, title="Vendor Compliance Tracker", verdict="Action", score=82)
            db.add(card)
            db.add(
                models.CandidateKeyword(
                    keyword="vendor compliance tracker",
                    source="suggest",
                    method="词找词",
                    score=0.82,
                    status="imported",
                    evidence_json='{"imported_query":"vendor compliance tracker","inputRef":{"type":"keyword","value":"compliance"}}',
                )
            )
            db.commit()

            clue = list_clues(db)["items"][0]

            self.assertEqual(clue["status"], "generated_opportunity")
            self.assertEqual(clue["keyword"]["id"], keyword.id)
            self.assertEqual(clue["opportunity"]["id"], card.id)
            self.assertEqual(clue["keyword_status"], "已入关键词库")
            self.assertEqual(clue["opportunity_status"], "已生成机会")
            self.assertEqual(clue["lifecycle_status"], "generated_opportunity")
            self.assertEqual(clue["lifecycle_status_label"], "已生成机会")

    def test_clue_llm_analysis_uses_configured_llm(self):
        original_llm_json = clue_pool.services._llm_json

        def fake_llm_json(db, system, user, temperature=0.2):
            return {
                "verdict": "长期关注",
                "summary": "这个词表达了明确的工具需求，适合继续跟踪。",
                "long_term_fit": "high",
                "reasoning": ["需求明确", "可承接"],
                "risks": ["需要确认是否只是品牌词"],
                "evidence_to_collect": ["SERP", "竞品"],
                "next_actions": ["补充 SERP 证据"],
            }

        clue_pool.services._llm_json = fake_llm_json
        try:
            with self.Session() as db:
                row = models.CandidateKeyword(
                    keyword="hermes agent",
                    source="suggest",
                    method="词找词",
                    score=0.74,
                    status="new",
                    evidence_json='{"inputRef":{"type":"keyword","value":"ai tools"}}',
                )
                db.add(row)
                db.commit()
                db.refresh(row)

                result = clue_pool.llm_analysis_for_clue(db, f"candidate_keyword:{row.id}")

                self.assertTrue(result["ok"])
                self.assertEqual(result["source"], "llm")
                self.assertEqual(result["analysis"]["verdict"], "长期关注")
                self.assertIn("SERP", result["analysis"]["evidence_to_collect"])
        finally:
            clue_pool.services._llm_json = original_llm_json


class CollectorSourceRunTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_manual_suggest_run_is_recorded_as_source_run(self):
        original = collector_endpoints.collectors.run_suggest_collector

        def fake_run(db, seeds):
            db.add(
                models.CandidateKeyword(
                    keyword="hermes agent software",
                    source="suggest",
                    method="词找词",
                    evidence_json='{"seed":"hermes agent"}',
                    score=0.61,
                    status="new",
                )
            )
            db.add(
                models.CandidateKeyword(
                    keyword="hermes ai agent",
                    source="suggest",
                    method="词找词",
                    evidence_json='{"seed":"hermes agent"}',
                    score=0.59,
                    status="new",
                )
            )
            db.commit()
            return {
                "ok": True,
                "source": "suggest",
                "seeds": len(seeds),
                "candidates_seen": 5,
                "saved": 2,
                "errors": [],
            }

        collector_endpoints.collectors.run_suggest_collector = fake_run
        try:
            with self.Session() as db:
                result = collector_endpoints.suggest_run(
                    schemas.CollectorSuggestIn(seeds=["hermes agent"], limit_per_seed=10),
                    _=True,
                    db=db,
                )
                rows = collector_endpoints.collector_source_runs(_=True, db=db)
        finally:
            collector_endpoints.collectors.run_suggest_collector = original

        self.assertEqual(result["saved"], 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "suggest")
        self.assertEqual(rows[0]["run_kind"], "manual")
        self.assertEqual(rows[0]["inputs"]["seeds"], ["hermes agent"])
        self.assertEqual(rows[0]["outputs"]["candidates_seen"], 5)
        self.assertEqual(rows[0]["candidates_created"], 2)
        self.assertEqual([item["keyword"] for item in rows[0]["outputs"]["candidates"]], ["hermes ai agent", "hermes agent software"])
        self.assertEqual([item["keyword"] for item in rows[0]["outputs"]["generatedClues"]], ["hermes ai agent", "hermes agent software"])
        self.assertEqual(rows[0]["outputs"]["generatedClues"][0]["inputRef"]["value"], "hermes agent")
        self.assertEqual(rows[0]["outputs"]["generatedClues"][0]["inputRef"]["type"], "keyword")

    def test_manual_run_errors_are_recorded_with_input_ref_and_retryable(self):
        original = collector_endpoints.collectors.run_suggest_collector

        def fake_run(db, seeds):
            return {
                "ok": True,
                "source": "suggest",
                "seeds": len(seeds),
                "candidates_seen": 0,
                "saved": 0,
                "errors": [{"seed": "hermes agent", "error": "suggest timeout"}],
            }

        collector_endpoints.collectors.run_suggest_collector = fake_run
        try:
            with self.Session() as db:
                collector_endpoints.suggest_run(
                    schemas.CollectorSuggestIn(seeds=["hermes agent"], limit_per_seed=10),
                    _=True,
                    db=db,
                )
                rows = collector_endpoints.collector_source_runs(_=True, db=db)
        finally:
            collector_endpoints.collectors.run_suggest_collector = original

        self.assertEqual(rows[0]["errors"][0]["message"], "suggest timeout")
        self.assertEqual(rows[0]["errors"][0]["inputRef"]["value"], "hermes agent")
        self.assertEqual(rows[0]["errors"][0]["inputRef"]["type"], "keyword")
        self.assertIs(rows[0]["errors"][0]["retryable"], True)

    def test_autopilot_run_records_generated_clues_with_input_ref(self):
        original = collector_endpoints.collectors.run_collector_autopilot

        def fake_run(db, limit, import_limit):
            db.add(
                models.CandidateKeyword(
                    keyword="hermes agent workflow",
                    source="suggest",
                    method="词找词",
                    evidence_json='{"seed":"hermes agent"}',
                    score=0.62,
                    status="new",
                )
            )
            db.commit()
            return {
                "enabled": True,
                "seeds": ["hermes agent"],
                "domains": [],
                "results": [{"source": "suggest", "saved": 1, "candidates_seen": 1, "errors": []}],
                "errors": [],
            }

        collector_endpoints.collectors.run_collector_autopilot = fake_run
        try:
            with self.Session() as db:
                collector_endpoints.collector_autopilot_run(
                    schemas.CandidateImportIn(limit=4),
                    _=True,
                    db=db,
                )
                rows = collector_endpoints.collector_source_runs(_=True, db=db)
        finally:
            collector_endpoints.collectors.run_collector_autopilot = original

        self.assertEqual(rows[0]["source"], "autopilot")
        self.assertEqual(rows[0]["run_kind"], "auto")
        self.assertEqual(rows[0]["outputs"]["generatedClues"][0]["keyword"], "hermes agent workflow")
        self.assertEqual(rows[0]["outputs"]["generatedClues"][0]["inputRef"]["value"], "hermes agent")

    def test_source_run_stats_are_not_limited_by_recent_rows(self):
        with self.Session() as db:
            for index in range(3):
                db.add(
                    models.SourceRun(
                        source="suggest",
                        run_kind="manual",
                        inputs_json='{"seeds":["hermes agent"]}',
                        outputs_json='{"candidates_seen": 5}',
                        candidates_created=2,
                        errors="[]",
                    )
                )
            db.add(
                models.SourceRun(
                    source="autopilot",
                    run_kind="auto",
                    inputs_json="{}",
                    outputs_json='{"candidates_seen": 1}',
                    candidates_created=1,
                    errors="[]",
                )
            )
            db.add(
                models.RunHistory(
                    kind="collector_autopilot",
                    status="success",
                    summary=json.dumps(
                        {
                            "source_results": [
                                {"source": "suggest", "seen": 4, "saved": 2, "errors": 0},
                                {"source": "sitemap", "seen": 8, "saved": 1, "errors": 1},
                            ]
                        }
                    ),
                )
            )
            db.commit()

            recent_rows = collector_endpoints.collector_source_runs(limit=2, _=True, db=db)
            stats = collector_endpoints.collector_source_run_stats(_=True, db=db)

        self.assertEqual(len(recent_rows), 2)
        self.assertEqual(stats["by_source"]["suggest"]["runs"], 4)
        self.assertEqual(stats["by_source"]["suggest"]["seen"], 19)
        self.assertEqual(stats["by_source"]["suggest"]["leads"], 8)
        self.assertEqual(stats["by_source"]["sitemap"]["runs"], 1)
        self.assertEqual(stats["by_source"]["sitemap"]["errors"], 1)


if __name__ == "__main__":
    unittest.main()
