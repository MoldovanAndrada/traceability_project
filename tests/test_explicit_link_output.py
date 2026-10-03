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

    def test_fault_story_associations_are_not_promoted_to_direct_links(self):
        docs = [
            {"id": "Bug-1", "type": "fault", "text": "US-101 | src/login.py"},
            {"id": "Bug-2", "type": "fault", "text": "US-202 | src/login.py"},
        ]
        graph = GraphStore(docs, embeddings=None)

        links = graph.explicit_links_for_text("US-101 | Reject an incorrect password")

        self.assertEqual(links, {})

    def test_fault_story_associations_support_dataset_specific_story_ids(self):
        docs = [
            {"id": "REQ-CHECKOUT", "type": "story", "text": "REQ-CHECKOUT | Checkout"},
            {
                "id": "DEFECT:CART",
                "type": "fault",
                "text": "DEFECT:CART | REQ-CHECKOUT | stale cart",
            },
        ]

        links = GraphStore(docs, embeddings=None).explicit_links_for_text(
            "REQ-CHECKOUT | Change checkout"
        )

        self.assertIn(0, links)
        self.assertNotIn(1, links)

    def test_explicit_fault_identifier_remains_a_direct_link(self):
        docs = [
            {"id": "US-101", "type": "story", "text": "US-101 | Login"},
            {"id": "Bug-1", "type": "fault", "text": "Bug-1 | US-101 | login.py"},
        ]

        links = GraphStore(docs, embeddings=None).explicit_links_for_text(
            "Investigate Bug-1"
        )

        self.assertEqual(links, {1: {"BUG-1"}})

    def test_artifact_prefixes_are_discovered_without_promoting_fault_history(self):
        docs = [
            {"id": "CHECK_81", "type": "test_case", "text": "CHECK_81 | REQ_204 | checkout"},
            {"id": "DEFECT:9", "type": "fault", "text": "DEFECT:9 | REQ_204 | stale cart"},
            {"id": "DEFECT:10", "type": "fault", "text": "DEFECT:10 | REQ_999 | other"},
        ]

        links = GraphStore(docs, embeddings=None).explicit_links_for_text(
            "REQ_204 | Change the checkout behaviour"
        )

        self.assertEqual(links, {0: {"REQ_204"}})

    def test_non_numeric_story_ids_are_discovered_from_dataset_artifacts(self):
        docs = [
            {"id": "REQ-CHECKOUT", "type": "story", "text": "REQ-CHECKOUT | Checkout"},
            {"id": "VERIFY-CART", "type": "test_case", "text": "VERIFY-CART | REQ-CHECKOUT"},
            {"id": "FAULT-CART", "type": "fault", "text": "FAULT-CART | REQ-CHECKOUT"},
        ]

        links = GraphStore(docs, embeddings=None).explicit_links_for_text(
            "REQ-CHECKOUT | Change the checkout behaviour"
        )

        self.assertEqual(
            links,
            {
                0: {"REQ-CHECKOUT"},
                1: {"REQ-CHECKOUT"},
            },
        )

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
