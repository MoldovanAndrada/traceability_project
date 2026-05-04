from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases

VALID_USER_STORY_FILES = {"user_stories.csv", "user_stories.xlsx", "user_stories.xls"}
EXPECTED_TEST_FILE = "test_cases.csv"
EXPECTED_FAULT_FILE = "faults.csv"

DETAILS_OUTPUT_PATH = BASE_DIR / "evaluation" / "requirement_ground_truth_results.csv"
SUMMARY_OUTPUT_PATH = BASE_DIR / "evaluation" / "requirement_ground_truth_summary.json"


def normalize_value(value: object) -> str:
    text = "" if value is None else str(value)
    return text.strip().replace("\\", "/").lower()


def normalize_set(value: object) -> set[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    text = str(value).replace(";", ",")
    parts = [normalize_value(part) for part in text.split(",")]
    return {part for part in parts if part}


def safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def compute_metrics(expected: set[str], predicted: set[str]) -> dict[str, float | int]:
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def find_dataset_dirs(root_dir: Path) -> list[Path]:
    datasets: list[Path] = []
    for current_root, _, files in os.walk(root_dir):
        file_set = {name.lower() for name in files}
        has_user_stories = any(name in file_set for name in VALID_USER_STORY_FILES)
        if has_user_stories and EXPECTED_TEST_FILE in file_set and EXPECTED_FAULT_FILE in file_set:
            datasets.append(Path(current_root))
    return sorted(datasets)


def find_user_stories_file(dataset_dir: Path) -> Path:
    for name in ["user_stories.csv", "user_stories.xlsx", "user_stories.xls"]:
        path = dataset_dir / name
        if path.exists():
            return path
    raise FileNotFoundError(f"No user stories file in {dataset_dir}")


def find_ground_truth_file(dataset_dir: Path) -> Path | None:
    candidates = sorted(
        p
        for p in dataset_dir.iterdir()
        if p.is_file()
        and "ground" in p.name.lower()
        and p.suffix.lower() in {".csv", ".xlsx", ".xls"}
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        print(f"Using ground truth file for {dataset_dir.name}: {candidates[0].name}")
    return candidates[0]


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def canonical_col_name(name: str) -> str:
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


def resolve_column(columns: Iterable[str], candidates: list[str], required: bool = True) -> str | None:
    canonical_map = {canonical_col_name(col): col for col in columns}
    for candidate in candidates:
        if candidate in canonical_map:
            return canonical_map[candidate]

    for col in columns:
        c = canonical_col_name(col)
        if any(candidate in c for candidate in candidates):
            return col

    if required:
        raise ValueError(f"Could not find required column with candidates {candidates}")
    return None


def build_story_text(row: pd.Series, columns: list[str], story_id_col: str) -> str:
    text_parts: list[str] = []
    preferred_cols = [
        col
        for col in columns
        if canonical_col_name(col) in {"featuresentence", "documentationtext", "title", "description", "text", "story"}
    ]

    source_cols = preferred_cols if preferred_cols else [col for col in columns if col != story_id_col]
    for col in source_cols:
        value = row.get(col)
        if value is None or (isinstance(value, float) and pd.isna(value)):
            continue
        value_str = str(value).strip()
        if value_str:
            text_parts.append(value_str)
    return "\n".join(text_parts)


def aggregate_metrics(rows: list[dict]) -> dict[str, float | int]:
    tp = sum(int(row["true_positives"]) for row in rows)
    fp = sum(int(row["false_positives"]) for row in rows)
    fn = sum(int(row["false_negatives"]) for row in rows)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main() -> None:
    dataset_dirs = find_dataset_dirs(BASE_DIR)

    detailed_rows: list[dict] = []
    evaluated_story_count = 0

    for dataset_dir in dataset_dirs:
        ground_truth_path = find_ground_truth_file(dataset_dir)
        if ground_truth_path is None:
            continue

        dataset_id = dataset_dir.name
        user_stories_df = read_table(find_user_stories_file(dataset_dir))
        ground_truth_df = read_table(ground_truth_path)

        user_story_id_col = resolve_column(user_stories_df.columns, ["userstoryid", "storyid", "id"])

        gt_story_id_col = resolve_column(ground_truth_df.columns, ["userstoryid", "storyid", "id"])
        gt_code_col = resolve_column(
            ground_truth_df.columns,
            ["expectedcodeclasses", "impactedcodeartifacts", "expectedcode", "codeclasses", "code"],
        )
        gt_tests_col = resolve_column(
            ground_truth_df.columns,
            ["expectedtestcases", "affectedtcsgroundtruth", "expectedtests", "testcases", "tests"],
        )
        gt_faults_col = resolve_column(
            ground_truth_df.columns,
            ["expectedfaults", "relevantfaultsgroundtruth", "faults", "bugs"],
        )

        stories_by_id = {
            normalize_value(row[user_story_id_col]): row for _, row in user_stories_df.iterrows()
        }

        for _, gt_row in ground_truth_df.iterrows():
            story_id = normalize_value(gt_row.get(gt_story_id_col))
            if not story_id:
                continue
            story_row = stories_by_id.get(story_id)
            if story_row is None:
                continue

            story_text = build_story_text(story_row, list(user_stories_df.columns), user_story_id_col)
            if not story_text.strip():
                continue

            evaluated_story_count += 1

            predicted_code = {
                normalize_value(result.get("id"))
                for result in get_impacted_code(story_text, dataset=dataset_id)
                if isinstance(result, dict) and result.get("id")
            }
            predicted_tests = {
                normalize_value(result.get("id"))
                for result in get_related_test_cases(story_text, dataset=dataset_id)
                if isinstance(result, dict) and result.get("id")
            }
            predicted_faults = {
                normalize_value(result.get("id"))
                for result in get_related_faults(story_text, dataset=dataset_id)
                if isinstance(result, dict) and result.get("id")
            }

            artifact_rows = [
                ("code", normalize_set(gt_row.get(gt_code_col)), predicted_code),
                ("test_cases", normalize_set(gt_row.get(gt_tests_col)), predicted_tests),
                ("faults", normalize_set(gt_row.get(gt_faults_col)), predicted_faults),
            ]

            for artifact_type, expected_set, predicted_set in artifact_rows:
                metrics = compute_metrics(expected_set, predicted_set)
                detailed_rows.append(
                    {
                        "dataset_id": dataset_id,
                        "user_story_id": story_id,
                        "artifact_type": artifact_type,
                        "expected": ",".join(sorted(expected_set)),
                        "predicted": ",".join(sorted(predicted_set)),
                        **metrics,
                    }
                )

    details_df = pd.DataFrame(
        detailed_rows,
        columns=[
            "dataset_id",
            "user_story_id",
            "artifact_type",
            "expected",
            "predicted",
            "true_positives",
            "false_positives",
            "false_negatives",
            "precision",
            "recall",
            "f1",
        ],
    )
    details_df.to_csv(DETAILS_OUTPUT_PATH, index=False)

    overall = aggregate_metrics(detailed_rows)

    per_dataset: dict[str, dict] = {}
    for dataset_id in sorted({row["dataset_id"] for row in detailed_rows}):
        rows = [row for row in detailed_rows if row["dataset_id"] == dataset_id]
        per_dataset[dataset_id] = aggregate_metrics(rows)

    per_artifact_type: dict[str, dict] = {}
    for artifact_type in sorted({row["artifact_type"] for row in detailed_rows}):
        rows = [row for row in detailed_rows if row["artifact_type"] == artifact_type]
        per_artifact_type[artifact_type] = aggregate_metrics(rows)

    summary = {
        "overall": {k: overall[k] for k in ("precision", "recall", "f1")},
        "per_dataset": {
            key: {k: value[k] for k in ("precision", "recall", "f1")}
            for key, value in per_dataset.items()
        },
        "per_artifact_type": {
            key: {k: value[k] for k in ("precision", "recall", "f1")}
            for key, value in per_artifact_type.items()
        },
    }
    SUMMARY_OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    evaluated_dataset_ids = {row["dataset_id"] for row in detailed_rows}
    print(f"Datasets evaluated: {len(evaluated_dataset_ids)}")
    print(f"User stories evaluated: {evaluated_story_count}")
    print(
        "Overall precision / recall / f1: "
        f"{overall['precision']:.4f} / {overall['recall']:.4f} / {overall['f1']:.4f}"
    )
    print(f"Detailed results: {DETAILS_OUTPUT_PATH}")
    print(f"Summary results: {SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
