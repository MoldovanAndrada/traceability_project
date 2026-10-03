import unittest

from src.dataset_utils import prefer_explicit_links


class StoryImpactSelectionTests(unittest.TestCase):
    def test_explicit_links_replace_inferred_candidates_of_same_type(self):
        records = [
            {"id": "TC-013", "type": "test_case", "link_type": "explicit"},
            {"id": "TC-018", "type": "test_case", "link_type": "inferred"},
            {"id": "Bug-035", "type": "fault", "link_type": "explicit"},
            {"id": "code.py", "type": "code", "link_type": "inferred"},
        ]

        selected = prefer_explicit_links(records)

        self.assertEqual(
            [record["id"] for record in selected],
            ["TC-013", "Bug-035", "code.py"],
        )

    def test_inferred_candidates_remain_when_type_has_no_explicit_link(self):
        records = [
            {"id": "TC-018", "type": "test_case", "link_type": "inferred"},
            {"id": "TC-007", "type": "test_case", "link_type": "inferred"},
        ]

        self.assertEqual(prefer_explicit_links(records), records)


if __name__ == "__main__":
    unittest.main()
