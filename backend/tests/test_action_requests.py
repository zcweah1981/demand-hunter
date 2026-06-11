import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.action_requests import create_action_request, execute_action_request, risk_for_action
from app.database import Base


class ActionRequestTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_contextual_recalculate_risk_is_low(self):
        self.assertEqual(risk_for_action("recalculate", "keyword"), "low")
        self.assertEqual(risk_for_action("recalculate", "opportunity_card"), "low")

    def test_high_risk_action_requires_confirmation(self):
        with self.Session() as db:
            request = create_action_request(db, "adopt", "opportunity_card", "1")

            result = execute_action_request(db, request.id, confirm=False)

            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "confirmation_required")
            db.refresh(request)
            self.assertEqual(request.status, "needs_confirmation")

    def test_low_risk_action_executes_and_audits(self):
        with self.Session() as db:
            request = create_action_request(db, "verify", "candidate_entry", "1")

            result = execute_action_request(db, request.id)

            self.assertTrue(result["ok"])
            db.refresh(request)
            self.assertEqual(request.status, "executed")
            self.assertEqual(db.query(models.ActionEvent).count(), 1)


if __name__ == "__main__":
    unittest.main()
