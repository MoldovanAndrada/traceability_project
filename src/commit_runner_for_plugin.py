import io
import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

import pandas as pd
import requests

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases, search
from src.code_watcher import get_latest_commit
from src.config import GITHUB_REPO, GITHUB_TOKEN

CODE_DIR_NAMES = {"code", "src"}
CODE_EXTENSIONS = {".java"}
STORY_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".md"}


def _get_file_content(sha: str, path: str) -> bytes | None:
    """Fetch file bytes for a given repo path at a specific commit SHA."""
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{sha}/{path}"
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        return None
    return response.content


def _extract_story_records(path: str, content: bytes | None) -> dict[str, str]:
    """Extract user-story records keyed by story ID when possible."""
    if not content:
        return {}

    suffix = path.lower().split(".")[-1]

    if suffix == "csv":
        df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="ignore")))
    elif suffix in {"xlsx", "xls"}:
        df = pd.read_excel(io.BytesIO(content))
    else:
        text = content.decode("utf-8", errors="ignore")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return {str(i): line for i, line in enumerate(lines, start=1)}

    id_columns = ["user_story_id", "story_id", "id"]
    text_columns = ["feature_sentence", "story", "description", "user_story", "documentation_text"]

    story_id_col = next((column for column in id_columns if column in df.columns), None)
    story_text_col = next((column for column in text_columns if column in df.columns), None)

    if story_text_col:
        text_values = df[story_text_col].fillna("").astype(str).str.strip()
        if story_id_col:
            id_values = df[story_id_col].fillna("").astype(str).str.strip()
            records = {
                sid: text
                for sid, text in zip(id_values.tolist(), text_values.tolist())
                if sid and text
            }
            if records:
                return records

        return {str(i): text for i, text in enumerate(text_values.tolist(), start=1) if text}

    stories: dict[str, str] = {}
    for column in df.columns:
        if pd.api.types.is_string_dtype(df[column]) or df[column].dtype == object:
            values = df[column].dropna().astype(str).str.strip()
            for value in values.tolist():
                if value:
                    key = str(len(stories) + 1)
                    stories[key] = value

    return stories


def _find_changed_stories(commit: dict[str, Any], filename: str) -> list[dict[str, str]]:
    """Compare story files between parent and current commit and return changed/new stories."""
    parent_sha = commit.get("parents", [{}])[0].get("sha")
    if not parent_sha:
        return []

    current_bytes = _get_file_content(commit["sha"], filename)
    previous_bytes = _get_file_content(parent_sha, filename)

    current_stories = _extract_story_records(filename, current_bytes)
    previous_stories = _extract_story_records(filename, previous_bytes)

    changed: list[dict[str, str]] = []
    for story_id, story_text in current_stories.items():
        if previous_stories.get(story_id) != story_text:
            changed.append({"id": story_id, "text": story_text})
    return changed


def _dataset_from_path(filename: str) -> str | None:
    parts = PurePosixPath(filename).parts
    if not parts:
        return None
    first = parts[0]
    if first.startswith("traceability_"):
        return first
    return None


def _is_code_class_file(filename: str) -> bool:
    path = PurePosixPath(filename)
    return path.suffix.lower() in CODE_EXTENSIONS and any(part in CODE_DIR_NAMES for part in path.parts)


def _is_story_file(filename: str) -> bool:
    lowered = filename.lower()
    return "story" in lowered and PurePosixPath(filename).suffix.lower() in STORY_EXTENSIONS


def _filter_artifact_types(records: list[dict[str, Any]], allowed_types: set[str]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("type") in allowed_types]


def run_once():
    commit = get_latest_commit()
    sha = commit["sha"]
    files = commit.get("files", [])

    code_changes_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    story_changes: list[dict[str, str]] = []

    for file_change in files:
        filename = file_change["filename"]
        dataset = _dataset_from_path(filename)
        if not dataset:
            continue

        if _is_code_class_file(filename):
            code_changes_by_dataset[dataset].append(file_change)
            continue

        if _is_story_file(filename):
            story_changes.append({"dataset": dataset, "filename": filename})

    impacted: list[dict[str, Any]] = []

    # Trigger analysis only for commits that modify at least one code class file.
    for dataset, code_changes in code_changes_by_dataset.items():
        for file_change in code_changes:
            patch_text = file_change.get("patch", "")
            if not patch_text:
                continue
            results = _filter_artifact_types(
                search(patch_text, dataset=dataset),
                {"story", "test_case", "fault"},
            )
            impacted.append(
                {
                    "trigger": "code_class_modified",
                    "dataset": dataset,
                    "file": file_change["filename"],
                    "results": results,
                }
            )

    # Trigger analysis for user story file modifications.
    for story_change in story_changes:
        dataset = story_change["dataset"]
        filename = story_change["filename"]
        changed_stories = _find_changed_stories(commit, filename)

        results: list[dict[str, Any]] = []
        for story in changed_stories:
            results.append({"type": "story", "id": story["id"], "text": story["text"]})
            story_results = []
            story_results.extend(get_related_test_cases(story["text"], dataset=dataset))
            story_results.extend(get_related_faults(story["text"], dataset=dataset))
            story_results.extend(get_impacted_code(story["text"], dataset=dataset))
            results.extend(story_results)

        impacted.append(
            {
                "trigger": "user_story_modified",
                "dataset": dataset,
                "file": filename,
                "results": results,
            }
        )

    print(json.dumps({"sha": sha, "impact": impacted}))


if __name__ == "__main__":
    run_once()
