import unittest

from src.dataset_utils import dataset_from_path, extract_story_changes_from_patch


class StoryPatchExtractionTest(unittest.TestCase):
    def test_detects_dataset_directory_with_a_space(self):
        self.assertEqual(
            dataset_from_path("dataset restbench/user_stories.csv"),
            "dataset restbench",
        )

    def test_extracts_deletion_only_changes(self):
        patch = '''diff --git a/user_stories.csv b/user_stories.csv
--- a/user_stories.csv
+++ b/user_stories.csv
@@ -1,2 +1 @@
-US-042,"As a user, I want deleted stories to be analyzed.",criteria
 US-043,"Unchanged story",criteria
'''

        self.assertEqual(
            extract_story_changes_from_patch(patch),
            [{
                "id": "US-042",
                "text": "As a user, I want deleted stories to be analyzed.",
                "change_type": "deleted",
            }],
        )

    def test_prefers_new_text_for_an_edited_story(self):
        patch = '''@@ -1 +1 @@
-US-008,"Old story text",old criteria
+US-008,"Updated story text",new criteria
'''

        self.assertEqual(
            extract_story_changes_from_patch(patch),
            [{
                "id": "US-008",
                "text": "Updated story text",
                "change_type": "added",
            }],
        )

if __name__ == "__main__":
    unittest.main()
