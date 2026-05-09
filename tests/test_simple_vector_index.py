import unittest

from src.indexer import SimpleVectorIndex


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


if __name__ == "__main__":
    unittest.main()
