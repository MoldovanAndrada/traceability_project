import unittest
from unittest.mock import patch

from src.agents import get_impacted_code


def _result(artifact_id, artifact_type, text, *, lexical=0.0, overlap=0.0):
    return {
        "id": artifact_id,
        "type": artifact_type,
        "text": text,
        "evidence": {
            "explicit_link": {"is_explicit": False, "matched_references": []},
            "factorized_explanation": {
                "bm25_index": {"score": lexical},
                "dense_index": {"score": 0.0},
                "reranker": {"query_artifact_overlap": overlap},
            },
            "confidence": {"abstain": True},
        },
    }


class CodeImpactRetrievalTests(unittest.TestCase):
    @patch("src.agents.search")
    def test_uses_relevant_dataset_context_without_domain_mappings(self, mock_search):
        direct_code = _result("src/DirectHandler.ext", "code", "direct behavior", lexical=0.8, overlap=0.4)
        related_test = _result("CASE-A", "test_case", "shared capability adapter", lexical=0.7, overlap=0.3)
        contextual_code = _result(
            "src/CapabilityAdapter.ext",
            "code",
            "shared capability adapter",
            lexical=0.9,
            overlap=0.5,
        )
        mock_search.side_effect = [[direct_code], [related_test], [contextual_code]]

        results = get_impacted_code("modify capability behavior", dataset="arbitrary-dataset")

        self.assertEqual(
            [result["id"] for result in results],
            ["src/DirectHandler.ext", "src/CapabilityAdapter.ext"],
        )
        self.assertEqual(mock_search.call_args_list[0].kwargs["artifact_types"], {"code"})
        self.assertEqual(
            mock_search.call_args_list[1].kwargs["artifact_types"],
            {"story", "test_case"},
        )
        expanded_query = mock_search.call_args_list[2].args[0]
        self.assertIn(related_test["text"], expanded_query)

    @patch("src.agents.search")
    def test_returns_no_code_when_retrieval_has_no_relevance_evidence(self, mock_search):
        forced_code_neighbor = _result("src/Unrelated.ext", "code", "unrelated implementation")
        forced_story_neighbor = _result("REQ-Z", "story", "unrelated requirement")
        mock_search.side_effect = [[forced_code_neighbor], [forced_story_neighbor]]

        results = get_impacted_code("terms absent from the corpus", dataset="arbitrary-dataset")

        self.assertEqual(results, [])
        self.assertEqual(mock_search.call_count, 2)


if __name__ == "__main__":
    unittest.main()
