import csv
import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases, search
from src.code_watcher import get_latest_commit

CODE_DIR_NAMES = {"code", "src"}
CODE_EXTENSIONS = {".java"}
STORY_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".md"}


def _search_with_dataset_fallback(query: str, dataset: str | None, allowed_types: set[str]) -> list[dict[str, Any]]:
    """Try dataset-aware search first, then fall back to global search when metadata lacks dataset tags."""
    results = _filter_artifact_types(search(query, dataset=dataset), allowed_types)
    if results or not dataset:
        return results
    return _filter_artifact_types(search(query), allowed_types)


def _extract_story_changes_from_patch(patch_text: str) -> list[dict[str, str]]:
    """Extract changed story rows from a git patch in a lightweight way."""
    changed: list[dict[str, str]] = []

    for line in patch_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue

        content = line[1:].strip()
        if not content:
            continue

        row = next(csv.reader([content]), None)
        if not row:
            continue

        row = [cell.strip() for cell in row if str(cell).strip()]
        if not row:
            continue

        if len(row) >= 2:
            changed.append({"id": row[0], "text": row[1]})
        else:
            changed.append({"id": str(len(changed) + 1), "text": row[0]})

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
    story_markers = ("story", "stories")
    return any(marker in lowered for marker in story_markers) and PurePosixPath(filename).suffix.lower() in STORY_EXTENSIONS


def _filter_artifact_types(records: list[dict[str, Any]], allowed_types: set[str]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("type") in allowed_types]


def _build_code_change_query(filename: str, patch_text: str) -> str:
    """Build a robust retrieval query for code changes.

    Git providers can omit/trim large patches, so we combine path-level context with
    patch content and still produce a useful query even when the patch is empty.
    """
    path = PurePosixPath(filename)
    class_name = path.stem

    if not patch_text:
        return f"{class_name} {path.name} {filename}"

    changed_lines = []
    for line in patch_text.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+") or line.startswith("-"):
            content = line[1:].strip()
            if content:
                changed_lines.append(content)

    # Keep query concise while preserving the most informative tokens.
    snippet = "\n".join(changed_lines[:80])
    return f"{class_name} {path.name} {filename}\n{snippet}".strip()


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
            query = _build_code_change_query(file_change["filename"], patch_text)
            results = _search_with_dataset_fallback(query, dataset, {"story", "test_case", "fault"})
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
        patch_text = next(
            (f.get("patch", "") for f in files if f.get("filename") == filename),
            "",
        )
        changed_stories = _extract_story_changes_from_patch(patch_text)

        results: list[dict[str, Any]] = []
        for story in changed_stories:
            results.append({"type": "story", "id": story["id"], "text": story["text"]})
            story_results = [
                *get_related_test_cases(story["text"], dataset=dataset),
                *get_related_faults(story["text"], dataset=dataset),
                *get_impacted_code(story["text"], dataset=dataset),
            ]
            if not story_results:
                story_results = [
                    *get_related_test_cases(story["text"]),
                    *get_related_faults(story["text"]),
                    *get_impacted_code(story["text"]),
                ]
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
