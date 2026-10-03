import unittest

from src.agents import _build_confidence_layer, _minmax_in_scope


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


if __name__ == "__main__":
    unittest.main()
