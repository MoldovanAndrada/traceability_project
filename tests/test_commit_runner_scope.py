import json
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("requests", types.SimpleNamespace(get=None))

from src.commit_runner_for_plugin import (
    _is_code_class_file,
    _is_story_file,
    _search_with_dataset_fallback,
    _supported_results,
    run_once,
)
from src.ingest import DATASET_CONFIG


class CommitRunnerScopeTests(unittest.TestCase):
    @patch("src.commit_runner_for_plugin.get_related_test_cases")
    @patch("src.commit_runner_for_plugin.search")
    @patch("src.commit_runner_for_plugin.get_latest_commit")
    def test_code_change_expands_surfaced_story_to_its_test_cases(
        self, mock_commit, mock_search, mock_test_cases
    ):
        mock_commit.return_value = {
            "sha": "abc123",
            "files": [
                {
                    "filename": "dataset restbench/src/handler.py",
                    "patch": "+return the updated resource",
                }
            ],
        }
        mock_search.return_value = [
            {
                "id": "US-007",
                "type": "story",
                "text": "Update an existing resource",
                "abstain": False,
                "evidence": {"explicit_link": {"is_explicit": False}},
            }
        ]
        mock_test_cases.return_value = [
            {
                "id": "TC-007",
                "type": "test_case",
                "text": "Verify an existing resource can be updated",
                "abstain": True,
                "evidence": {
                    "explicit_link": {
                        "is_explicit": True,
                        "matched_references": ["US-007"],
                    }
                },
            }
        ]

        with patch("builtins.print") as mock_print:
            run_once()

        payload = json.loads(mock_print.call_args.args[0])
        result_ids = [record["id"] for record in payload["impact"][0]["results"]]
        self.assertEqual(result_ids, ["US-007", "TC-007"])
        mock_test_cases.assert_called_once_with(
            "US-007 | Update an existing resource", dataset="dataset restbench"
        )
        self.assertIn("[test_case]: TC-007", payload["human_readable_report"])

    @patch("src.commit_runner_for_plugin.get_impacted_code")
    @patch("src.commit_runner_for_plugin.get_related_faults")
    @patch("src.commit_runner_for_plugin.get_related_test_cases")
    @patch("src.commit_runner_for_plugin.get_latest_commit")
    def test_story_changes_omit_abstained_inferred_candidates_but_keep_explicit_links(
        self, mock_commit, mock_test_cases, mock_faults, mock_impacted_code
    ):
        mock_commit.return_value = {
            "sha": "abc123",
            "files": [
                {
                    "filename": "dataset restbench/user_stories.csv",
                    "patch": "+US-003,As a user I want missing items reported",
                }
            ],
        }
        mock_test_cases.return_value = [
            {
                "id": "TC-009",
                "type": "test_case",
                "link_type": "inferred",
                "abstain": True,
                "evidence": {"explicit_link": {"is_explicit": False}},
            },
            {
                "id": "TC-003",
                "type": "test_case",
                "link_type": "explicit",
                "abstain": True,
                "evidence": {"explicit_link": {"is_explicit": True}},
            },
        ]
        mock_faults.return_value = [
            {
                "id": "Bug-004",
                "type": "fault",
                "link_type": "inferred",
                "abstain": True,
                "evidence": {"explicit_link": {"is_explicit": False}},
            }
        ]
        mock_impacted_code.return_value = []

        with patch("builtins.print") as mock_print:
            run_once()

        payload = json.loads(mock_print.call_args.args[0])
        result_ids = [record["id"] for record in payload["impact"][0]["results"]]
        self.assertEqual(result_ids, ["US-003", "TC-003"])
        self.assertIn("[test_case]: TC-003", payload["human_readable_report"])
        self.assertNotIn("TC-009", payload["human_readable_report"])
        self.assertNotIn("Bug-004", payload["human_readable_report"])

    def test_artifact_detection_uses_each_dataset_ingestion_config(self):
        for dataset, config in DATASET_CONFIG.items():
            with self.subTest(dataset=dataset, artifact="story"):
                self.assertTrue(
                    _is_story_file(f"{dataset}/{config['stories']}", dataset)
                )

            code_dir = (config.get("code_dirs") or [config["code_dir"]])[0]
            extension = config.get("code_globs", ["*.java"])[0].removeprefix("*")
            with self.subTest(dataset=dataset, artifact="code"):
                self.assertTrue(
                    _is_code_class_file(
                        f"{dataset}/{code_dir}/nested/example{extension}", dataset
                    )
                )

    def test_ground_truth_is_not_misclassified_as_a_story_inventory(self):
        self.assertFalse(
            _is_story_file(
                "dataset libEST/ground_truth.csv",
                "dataset libEST",
            )
        )

    @patch("src.commit_runner_for_plugin.get_impacted_code")
    @patch("src.commit_runner_for_plugin.search")
    @patch("src.commit_runner_for_plugin.get_latest_commit")
    def test_dataset_test_case_changes_do_not_trigger_analysis(
        self, mock_commit, mock_search, mock_impacted_code
    ):
        mock_commit.return_value = {
            "sha": "abc123",
            "files": [
                {
                    "filename": "dataset restbench/test_cases.csv",
                    "patch": "-TC-007,FastAPI - Update nonexistent item,US-007",
                }
            ],
        }

        with patch("builtins.print") as mock_print:
            run_once()

        payload = json.loads(mock_print.call_args.args[0])
        self.assertEqual(payload["impact"], [])
        self.assertNotIn("Modified File:", payload["human_readable_report"])
        mock_search.assert_not_called()
        mock_impacted_code.assert_not_called()

    @patch("src.commit_runner_for_plugin.get_impacted_code")
    @patch("src.commit_runner_for_plugin.search")
    @patch("src.commit_runner_for_plugin.get_latest_commit")
    def test_repository_source_and_test_changes_do_not_trigger_analysis(
        self, mock_commit, mock_search, mock_impacted_code
    ):
        mock_commit.return_value = {
            "sha": "abc123",
            "files": [
                {"filename": "src/agents.py", "patch": "+logic"},
                {"filename": "tests/test_code_impact_retrieval.py", "patch": "+test"},
            ],
        }

        with patch("builtins.print") as mock_print:
            run_once()

        payload = json.loads(mock_print.call_args.args[0])
        self.assertEqual(payload["impact"], [])
        mock_search.assert_not_called()
        mock_impacted_code.assert_not_called()

    @patch("src.commit_runner_for_plugin.search")
    def test_dataset_search_does_not_fall_back_to_global_corpus(self, mock_search):
        mock_search.return_value = []

        results = _search_with_dataset_fallback("change", "traceability_lang", {"story"})

        self.assertEqual(results, [])
        mock_search.assert_called_once_with(
            "change", dataset="traceability_lang", artifact_types={"story"}
        )

    def test_abstained_inferences_are_not_reported(self):
        explicit = {
            "id": "TC-1",
            "abstain": True,
            "evidence": {"explicit_link": {"is_explicit": True}},
        }
        supported = {
            "id": "TC-2",
            "abstain": False,
            "evidence": {"explicit_link": {"is_explicit": False}},
        }
        unsupported = {
            "id": "TC-3",
            "abstain": True,
            "evidence": {"explicit_link": {"is_explicit": False}},
        }

        self.assertEqual(_supported_results([explicit, supported, unsupported]), [explicit, supported])


if __name__ == "__main__":
    unittest.main()
