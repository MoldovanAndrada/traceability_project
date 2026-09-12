import unittest

from src.dataset_utils import dataset_from_path


class DatasetFromPathTest(unittest.TestCase):
    def test_recognizes_dataset_directories_separated_by_spaces(self):
        self.assertEqual(
            dataset_from_path("dataset safa/src/main/java/Example.java"),
            "dataset safa",
        )
        self.assertEqual(
            dataset_from_path("dataset restbench/tests/api_test.py"),
            "dataset restbench",
        )

    def test_preserves_existing_dataset_naming_conventions(self):
        self.assertEqual(dataset_from_path("dataset-api/src/server.go"), "dataset-api")
        self.assertEqual(dataset_from_path("traceability_lang/code/StringUtils.java"), "traceability_lang")

    def test_ignores_regular_top_level_directories(self):
        self.assertIsNone(dataset_from_path("src/main.py"))


if __name__ == "__main__":
    unittest.main()
