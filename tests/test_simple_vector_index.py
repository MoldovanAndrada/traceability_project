import unittest

import numpy as np

from src.indexer import FaissVectorIndex, SimpleVectorIndex


class AmbiguousArrayLike:
    """Array-like object that mimics NumPy's ambiguous truth-value behavior."""

    def __init__(self, values):
        self.values = values

    def __bool__(self):
        raise ValueError("The truth value of an array with more than one element is ambiguous")

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]

    def tolist(self):
        return self.values


class SimpleVectorIndexTest(unittest.TestCase):
    def test_search_accepts_numpy_like_query_without_truth_testing(self):
        index = SimpleVectorIndex([[0.0, 0.0], [1.0, 1.0]])

        distances, indices = index.search(AmbiguousArrayLike([[0.0, 0.0]]), k=2)

        self.assertEqual(indices, [[0, 1]])
        self.assertEqual(distances[0][0], 0.0)


class RecordingFaissIndex:
    d = 2
    ntotal = 1

    def search(self, queries, k):
        self.queries = queries
        return np.array([[0.0]]), np.array([[0]])


class FaissVectorIndexTest(unittest.TestCase):
    def test_search_converts_list_query_to_contiguous_float32_array(self):
        raw_index = RecordingFaissIndex()
        index = FaissVectorIndex(raw_index, np)

        index.search([[1, 2]], k=1)

        self.assertEqual(raw_index.queries.dtype, np.float32)
        self.assertTrue(raw_index.queries.flags.c_contiguous)

    def test_search_reports_dimension_mismatch_clearly(self):
        index = FaissVectorIndex(RecordingFaissIndex(), np)

        with self.assertRaisesRegex(ValueError, "Re-run ingest.py"):
            index.search([[1, 2, 3]], k=1)


if __name__ == "__main__":
    unittest.main()
