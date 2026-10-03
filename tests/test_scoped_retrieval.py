import unittest

from src.agents import (
    _build_confidence_layer,
    _minmax_in_scope,
    _select_top_k_with_explicit_links,
)


class ScopedRetrievalTests(unittest.TestCase):
    def test_normalization_ignores_out_of_scope_corpus_scores(self):
        scores = [100.0, 2.0, 4.0, 50.0]

        normalized = _minmax_in_scope(scores, [1, 2])

        self.assertEqual(normalized, [0.0, 0.0, 1.0, 0.0])

    def test_independent_support_survives_a_dominant_graph_signal(self):
        confidence = _build_confidence_layer(
            dense_score=0.56,
            lexical_score=0.53,
            graph_score=1.0,
            final_score=0.44,
            reranker={},
        )

        self.assertEqual(
            confidence["source_of_support"],
            ["graph", "semantic", "lexical"],
        )
        self.assertFalse(confidence["abstain"])

    def test_explicit_links_share_the_top_k_result_budget(self):
        selected = _select_top_k_with_explicit_links(
            ranked_indices=[0, 1, 2, 3, 4],
            explicit_links={1: {"US-1"}, 3: {"US-1"}},
            k=3,
        )

        self.assertEqual(selected, [1, 3, 0])
        self.assertEqual(len(selected), 3)

    def test_explicit_links_are_bounded_when_they_exceed_top_k(self):
        selected = _select_top_k_with_explicit_links(
            ranked_indices=[0, 1, 2, 3],
            explicit_links={0: {"US-1"}, 1: {"US-1"}, 2: {"US-1"}},
            k=2,
        )

        self.assertEqual(selected, [0, 1])


if __name__ == "__main__":
    unittest.main()
