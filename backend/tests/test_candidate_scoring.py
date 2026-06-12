import unittest

from app.candidate_scoring import candidate_is_importable, score_candidate, score_candidate_detail


class CandidateScoringTests(unittest.TestCase):
    def test_unified_score_exposes_quality_dimensions(self):
        result = score_candidate_detail(
            "vendor compliance tracker template",
            source="suggest",
            evidence={"inputRef": {"type": "keyword", "value": "vendor compliance"}, "provider": "serpapi"},
            seed="vendor compliance",
        )

        self.assertGreater(result["candidate_quality_score"], 0.65)
        self.assertGreater(result["demand_signal_score"], 70)
        self.assertGreaterEqual(result["source_confidence_score"], 50)
        self.assertEqual(result["gate"], "pass")
        self.assertIn("breakdown", result)
        self.assertTrue(any(item["dimension"] == "demand" for item in result["breakdown"]))

    def test_unified_score_blocks_four_find_noise_with_reasons(self):
        result = score_candidate_detail(
            "vendor compliance facebook",
            source="four_find",
            seed="vendor compliance",
            source_domain="facebook.com",
        )

        self.assertLess(result["candidate_quality_score"], 0.68)
        self.assertEqual(result["gate"], "reject")
        self.assertIn("weak_source_domain", result["reasons"])
        self.assertFalse(candidate_is_importable("vendor compliance", "vendor compliance facebook", "facebook.com"))

    def test_legacy_score_candidate_uses_unified_score(self):
        detail = score_candidate_detail("invoice payment reminder template", source="sitemap", evidence={"is_new_url": True})

        self.assertEqual(score_candidate("invoice payment reminder template", "sitemap", {"is_new_url": True}), detail["candidate_quality_score"])
        self.assertGreater(detail["trend_signal_score"], 50)


if __name__ == "__main__":
    unittest.main()
