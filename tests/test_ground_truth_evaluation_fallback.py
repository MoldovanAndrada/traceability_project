import unittest

from evaluation.ground_truth_evaluation import _dataset_search


class GroundTruthEvaluationFallbackTest(unittest.TestCase):
    def test_dataset_search_falls_back_on_ambiguous_truth_value_error(self):
        records = [
            {
                "dataset": "traceability_lang",
                "type": "test_case",
                "id": "TC-001",
                "text": "normalize whitespace and capitalize accents",
            },
            {
                "dataset": "other_dataset",
                "type": "test_case",
                "id": "TC-999",
                "text": "normalize whitespace and capitalize accents",
            },
        ]

        def failing_agent_search(query, k, dataset):
            raise ValueError("The truth value of an array with more than one element is ambiguous")

        results = _dataset_search(
            "normalize whitespace",
            "traceability_lang",
            records,
            failing_agent_search,
            k=10,
        )

        self.assertEqual([result["id"] for result in results], ["TC-001"])


if __name__ == "__main__":
    unittest.main()
