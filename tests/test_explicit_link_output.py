import unittest

from src.explainability import format_explanation
from src.graph_store import GraphStore
from src.dataset_utils import build_story_change_query


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

    def test_changed_story_id_returns_test_case_linked_by_user_story_column(self):
        query = build_story_change_query(
            {
                "id": "US-101",
                "text": "The newly edited prose does not repeat the story identifier.",
            }
        )

        links = self.graph.explicit_links_for_text(query)

        self.assertIn(1, links)
        self.assertEqual(links[1], {"US-101"})

    def test_shared_file_neighbor_is_not_mislabeled_as_direct_story_link(self):
        docs = [
            {"id": "Bug-1", "type": "fault", "text": "US-101 | src/login.py"},
            {"id": "Bug-2", "type": "fault", "text": "US-202 | src/login.py"},
        ]
        graph = GraphStore(docs, embeddings=None)

        links = graph.explicit_links_for_text("US-101 | Reject an incorrect password")

        self.assertEqual(links, {0: {"US-101"}})

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
