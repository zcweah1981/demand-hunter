import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
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


if __name__ == "__main__":
    unittest.main()
