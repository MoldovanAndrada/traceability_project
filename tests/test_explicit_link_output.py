import unittest

from src.explainability import format_explanation
from src.graph_store import GraphStore


class ExplicitLinkOutputTests(unittest.TestCase):
    def setUp(self):
        self.docs = [
            {"id": "US-101", "type": "story", "text": "US-101 | Export a report"},
            {
                "id": "TC-9",
                "type": "test_case",
                "text": "TC-9 | Export test | US-101 | click Export",
            },
            {"id": "US-202", "type": "story", "text": "US-202 | Delete a report"},
        ]
        self.graph = GraphStore(self.docs, embeddings=None)

    def test_test_case_input_returns_its_explicit_story(self):
        links = self.graph.explicit_links_for_text(
            "test_case_id,test_case_title,user_story_id\nTC-9,Export test,US-101"
        )

        self.assertIn(0, links)
        self.assertEqual(links[0], {"US-101"})
        self.assertNotIn(2, links)

    def test_explanation_labels_explicit_link_and_reference(self):
        result = {
            "evidence": {
                "factorized_explanation": {},
                "explicit_link": {"is_explicit": True, "matched_references": ["US-101"]},
            }
        }
        # A result produced by search has factorized evidence; include the minimum
        # fields needed to exercise the normal formatter path.
        result["evidence"]["factorized_explanation"] = {
            "dense_index": {},
            "bm25_index": {},
            "graph_index": {},
        }

        explanation = format_explanation(result)

        self.assertIn("explicit link via [US-101]", explanation)


if __name__ == "__main__":
    unittest.main()
