import unittest

from app import models


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


if __name__ == "__main__":
    unittest.main()
