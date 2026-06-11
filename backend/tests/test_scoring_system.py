import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.discovery_entries import route_entry_next_action, upsert_candidate_entry
from app.scoring_system import score_demand_keyword, score_trend_entity


class CandidateEntryRoutingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_search_keyword_routes_to_demand_scoring(self):
        with self.Session() as db:
            entry = upsert_candidate_entry(db, "search_keyword", "shopify tax calculator", source="test")

            self.assertEqual(route_entry_next_action(entry), "score_demand_keyword")

    def test_trend_like_entries_route_to_trend_scoring(self):
        trend_types = ["trend_entity", "github_repo", "game", "platform_update"]

        for entry_type in trend_types:
            with self.subTest(entry_type=entry_type), self.Session() as db:
                entry = upsert_candidate_entry(db, entry_type, f"{entry_type} sample", source="test")

                self.assertEqual(route_entry_next_action(entry), "score_trend_entity")

    def test_evidence_derived_entry_stays_out_of_keywords(self):
        with self.Session() as db:
            entry = upsert_candidate_entry(
                db,
                "search_keyword",
                "game build planner",
                source="sitemap_monitor",
                source_role="evidence",
                raw_context={"derived_from_evidence_id": 1},
            )

            keyword_count = db.query(models.Keyword).count()
            self.assertEqual(keyword_count, 0)
            self.assertEqual(entry.status, "new")
            self.assertEqual(route_entry_next_action(entry), "score_demand_keyword")


class SplitScoringTests(unittest.TestCase):
    def test_demand_keyword_score_has_quality_gate(self):
        result = score_demand_keyword("shopify tax calculator")

        self.assertIn("score", result)
        self.assertIn("breakdown", result)
        self.assertIn("quality_gate", result)
        self.assertIn("demand_clarity", result["breakdown"])
        self.assertIn("commercial_intent", result["breakdown"])

    def test_trend_entity_score_requires_translation_before_keywords(self):
        result = score_trend_entity("OpenClaw")

        self.assertIn("score", result)
        self.assertIn("breakdown", result)
        self.assertIn("next_action", result)
        self.assertIn("translation_potential", result["breakdown"])
        self.assertNotEqual(result["next_action"], "promote_to_keywords")


if __name__ == "__main__":
    unittest.main()
