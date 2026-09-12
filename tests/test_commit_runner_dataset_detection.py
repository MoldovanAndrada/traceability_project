import unittest

from src.dataset_utils import dataset_from_path, extract_story_changes_from_patch


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


class StoryPatchExtractionTest(unittest.TestCase):
    def test_extracts_stories_from_deletion_only_patch(self):
        patch = '''diff --git a/user_stories.csv b/user_stories.csv
--- a/user_stories.csv
+++ b/user_stories.csv
@@ -1,2 +1 @@
-US-042,"As a superuser, I want a clear not-found response.",Acceptance criteria
 US-043,"Unchanged story",Acceptance criteria
'''

        self.assertEqual(
            extract_story_changes_from_patch(patch),
            [
                {
                    "id": "US-042",
                    "text": "As a superuser, I want a clear not-found response.",
                    "change_type": "deleted",
                }
            ],
        )

    def test_uses_added_text_once_when_story_is_updated(self):
        patch = '''@@ -1 +1 @@
-US-008,"Old story text",Old criteria
+US-008,"Updated story text",Updated criteria
'''

        self.assertEqual(
            extract_story_changes_from_patch(patch),
            [
                {
                    "id": "US-008",
                    "text": "Updated story text",
                    "change_type": "added",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
