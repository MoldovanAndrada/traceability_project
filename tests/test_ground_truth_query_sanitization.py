import unittest

from evaluation.ground_truth_evaluation import _sanitize_query


class GroundTruthQuerySanitizationTest(unittest.TestCase):
    def test_uses_post_change_text_and_removes_benchmark_labels(self):
        raw = (
            "US-01 (Normalize+Capitalize): V1: Capitalize only. → "
            "V2: Normalize whitespace + remove accents + capitalize via facade."
        )

        self.assertEqual(
            _sanitize_query(raw),
            "Normalize whitespace remove accents capitalize via facade",
        )

    def test_removes_artifact_ids(self):
        self.assertEqual(
            _sanitize_query("V2: update TC-001 and Bug-01 handling for US-02"),
            "update and handling for",
        )


if __name__ == "__main__":
    unittest.main()
