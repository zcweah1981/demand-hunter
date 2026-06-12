import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
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


if __name__ == "__main__":
    unittest.main()
