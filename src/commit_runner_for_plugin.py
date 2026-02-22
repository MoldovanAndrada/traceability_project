import io
import json
from typing import Any

import pandas as pd
import requests

from src.code_watcher import get_latest_commit
from src.agents import (
    get_impacted_code,
    get_related_faults,
    get_related_test_cases,
    search,
)
from src.config import GITHUB_REPO, GITHUB_TOKEN


def _get_file_content(sha: str, path: str) -> bytes | None:
    """Fetch file bytes for a given repo path at a specific commit SHA."""
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{sha}/{path}"
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        return None
    return response.content


def _extract_story_texts(path: str, content: bytes | None) -> set[str]:
    """Extract story texts from common user-story file formats."""
    if not content:
        return set()

    suffix = path.lower().split(".")[-1]

    if suffix == "csv":
        df = pd.read_csv(io.StringIO(content.decode("utf-8", errors="ignore")))
    elif suffix in {"xlsx", "xls"}:
        df = pd.read_excel(io.BytesIO(content))
    else:
        text = content.decode("utf-8", errors="ignore")
        return {line.strip() for line in text.splitlines() if line.strip()}

    # Prefer known columns, then fallback to all string columns.
    known_columns = [
        "feature_sentence",
        "story",
        "description",
        "user_story",
    ]
    for column in known_columns:
        if column in df.columns:
            values = df[column].dropna().astype(str).str.strip()
            return {v for v in values.tolist() if v}

    stories: set[str] = set()
    for column in df.columns:
        if pd.api.types.is_string_dtype(df[column]) or df[column].dtype == object:
            values = df[column].dropna().astype(str).str.strip()
            stories.update(v for v in values.tolist() if v)

    return stories


def _find_changed_stories(commit: dict[str, Any], filename: str) -> list[str]:
    """Compare story files between parent and current commit and return changed/new stories."""
    parent_sha = commit.get("parents", [{}])[0].get("sha")
    if not parent_sha:
        return []

    current_bytes = _get_file_content(commit["sha"], filename)
    previous_bytes = _get_file_content(parent_sha, filename)

    current_stories = _extract_story_texts(filename, current_bytes)
    previous_stories = _extract_story_texts(filename, previous_bytes)

    return sorted(current_stories - previous_stories)


def _is_story_file(filename: str) -> bool:
    lowered = filename.lower()
    return "story" in lowered and lowered.endswith((".csv", ".xlsx", ".xls", ".txt", ".md"))

def run_once():
    commit = get_latest_commit()
    sha = commit["sha"]

    impacted = []

    for f in commit["files"]:
        filename = f["filename"]
        text = f.get("patch", "")

        # Default impact analysis for code/documentation diffs.
        results = search(text) if text else []

        # Additional analysis for changed user stories.
        if _is_story_file(filename):
            changed_stories = _find_changed_stories(commit, filename)
            for story in changed_stories:
                story_results = []
                story_results.extend(get_related_test_cases(story))
                story_results.extend(get_related_faults(story))
                story_results.extend(get_impacted_code(story))
                results.extend(story_results)

        impacted.append({
            "file": filename,
            "results": results
        })

    print(json.dumps({
        "sha": sha,
        "impact": impacted
    }))

if __name__ == "__main__":
    run_once()
