import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

import requests

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases, search
from src.code_watcher import get_latest_commit
from src.config import GITHUB_REPO
from src.dataset_utils import (
    build_story_change_query,
    dataset_from_path,
    extract_story_changes_from_patch,
    prefer_explicit_links,
)
from src.explainability import format_explanation

CODE_DIR_NAMES = {"code", "src", "app-react-frontend", "app-react-content"}
CODE_EXTENSIONS = {".java", ".go", ".py", ".js", ".ts", ".tsx", ".c", ".cpp", ".cs", ".css"}
STORY_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".md"}
TEST_FILE_MARKERS = ("test", "tests", "spec", "specs")


def _search_with_dataset_fallback(query: str, dataset: str | None, allowed_types: set[str]) -> list[dict[str, Any]]:
    """Try dataset-aware search first, then fall back to global search when metadata lacks dataset tags."""
    results = search(query, dataset=dataset, artifact_types=allowed_types)
    if results or not dataset:
        return results
    return search(query, artifact_types=allowed_types)


def _extract_story_changes_from_patch(patch_text: str) -> list[dict[str, str]]:
    """Backward-compatible wrapper for story patch extraction."""
    return extract_story_changes_from_patch(patch_text)


def _dataset_from_path(filename: str) -> str | None:
    return dataset_from_path(filename)


def _is_code_class_file(filename: str) -> bool:
    path = PurePosixPath(filename)
    return path.suffix.lower() in CODE_EXTENSIONS and any(part in CODE_DIR_NAMES for part in path.parts)


def _is_story_file(filename: str) -> bool:
    lowered = filename.lower()
    story_markers = ("story", "stories")
    return any(marker in lowered for marker in story_markers) and PurePosixPath(filename).suffix.lower() in STORY_EXTENSIONS


def _is_test_artifact_file(filename: str) -> bool:
    """Recognize both test inventories and executable tests across datasets."""
    path = PurePosixPath(filename)
    parts = tuple(part.lower() for part in path.parts)
    stem = path.stem.lower()
    return any(
        marker in stem or marker in parts
        for marker in TEST_FILE_MARKERS
    )


def _filter_artifact_types(records: list[dict[str, Any]], allowed_types: set[str]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("type") in allowed_types]


def _attach_explanations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a human-readable explanation to every retrieved artifact result.

    Guarantees:
      - every record has a non-empty `explanation`
      - no duplicated alias keys
      - adds `display` for convenience
    """
    explained: list[dict[str, Any]] = []

    for record in records:
        enriched = dict(record)

        # Optional story context
        if enriched.get("type") == "story":
            story_text = (enriched.get("text") or "").strip()
            change_type = enriched.get("change_type", "changed")
            enriched["explanation_reason"] = (
                f"story {change_type} in commit; text snippet='{story_text[:80]}'"
                if story_text
                else f"story {change_type} in commit"
            )

        # Try your existing formatter first
        explanation = (format_explanation(enriched) or "").strip()

        # Hard fallback: ensure explanation is never empty
        if not explanation:
            rtype = enriched.get("type") or "artifact"
            rid = enriched.get("id") or "unknown"

            # Prefer story-specific hint if available
            story_hint = (enriched.get("explanation_reason") or "").strip()
            if story_hint:
                explanation = story_hint
            else:
                explanation = f"{rtype} surfaced as related to the recent change (id={rid})"

        enriched["explanation"] = explanation

        # Convenience string if you want to print directly
        enriched["display"] = f"[{enriched.get('type','unknown')}] {enriched.get('id','unknown')} -> {explanation}"

        explained.append(enriched)

    return explained


def _record_key(record: dict[str, Any]) -> tuple[str, str]:
    return str(record.get("type", "unknown")), str(record.get("id", "unknown"))


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = _record_key(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _fetch_file_content_at_commit(sha: str, filename: str) -> str:
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{sha}/{filename}"
    response = requests.get(url, timeout=20)
    if response.status_code != 200:
        return ""
    return response.text


def _extract_story_changes(file_change: dict[str, Any], sha: str) -> list[dict[str, str]]:
    patch_text = file_change.get("patch", "")
    changed_stories = _extract_story_changes_from_patch(patch_text)
    if changed_stories:
        return changed_stories

    # GitHub can omit the patch for large files. Fall back to current file content
    # so story updates still produce impact output instead of an empty result.
    filename = file_change.get("filename", "")
    if not filename:
        return []
    file_content = _fetch_file_content_at_commit(sha, filename)
    return _extract_story_changes_from_patch("\n".join(f"+{line}" for line in file_content.splitlines()))


def _result_line(result: dict[str, Any]) -> str:
    rtype = result.get("type", "unknown")
    rid = result.get("id", "unknown")
    explanation = result.get("explanation") or result.get("reason") or "explanation unavailable"
    prefix = f"[{rtype}]:"
    return f"{prefix} {rid} -> {explanation}"


def _impact_block_lines(block: dict[str, Any]) -> list[str]:
    lines = [f"Modified File: {block['file']}"]
    for result in block.get("results", []):
        lines.append(f" • {_result_line(result)}")
    return lines


def run_once():
    commit = get_latest_commit()
    sha = commit["sha"]
    files = commit.get("files", [])

    code_changes_by_dataset: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    test_changes_by_dataset: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    story_changes: list[dict[str, str | None]] = []

    for file_change in files:
        filename = file_change["filename"]
        dataset = _dataset_from_path(filename)
        if _is_test_artifact_file(filename):
            test_changes_by_dataset[dataset].append(file_change)
            continue
        if _is_code_class_file(filename):
            code_changes_by_dataset[dataset].append(file_change)
            continue

        if _is_story_file(filename):
            story_changes.append({"dataset": dataset, "filename": filename})

    impacted: list[dict[str, Any]] = []

    # A changed test is itself impact evidence.  Search code in a dedicated
    # type-constrained result set so Login/User/Profile implementations cannot
    # be crowded out by abundant test-case or fault records.
    for dataset, test_changes in test_changes_by_dataset.items():
        for file_change in test_changes:
            filename = file_change["filename"]
            query = f"Modified test: {filename}\n{file_change.get('patch', '')}".strip()
            if not query:
                continue
            results = [
                *_search_with_dataset_fallback(query, dataset, {"story", "test_case", "fault"}),
                *get_impacted_code(query, dataset=dataset),
            ]
            if not any(result.get("type") == "code" for result in results) and dataset:
                results.extend(get_impacted_code(query))
            normalized_filename = filename.replace("\\", "/").lower()
            results = [
                result
                for result in results
                if not (
                    result.get("type") == "code"
                    and str(result.get("path") or result.get("id", "")).replace("\\", "/").lower()
                    == normalized_filename
                )
            ]
            block = {
                "trigger": "test_modified",
                "dataset": dataset,
                "file": filename,
                "results": _dedupe_records(_attach_explanations(results)),
            }
            block["summary_lines"] = _impact_block_lines(block)
            impacted.append(block)

    # Trigger analysis only for commits that modify at least one code class file.
    for dataset, code_changes in code_changes_by_dataset.items():
        for file_change in code_changes:
            patch_text = file_change.get("patch", "")
            if not patch_text:
                continue
            results = _search_with_dataset_fallback(patch_text, dataset, {"story", "test_case", "fault"})
            explained_results = _attach_explanations(results)
            block = {
                "trigger": "code_class_modified",
                "dataset": dataset,
                "file": file_change["filename"],
                "results": explained_results,
            }
            block["summary_lines"] = _impact_block_lines(block)
            impacted.append(block)

    # Trigger analysis for user story file modifications.
    for story_change in story_changes:
        dataset = story_change["dataset"]
        filename = story_change["filename"]
        file_change = next(
            (f for f in files if f.get("filename") == filename),
            {},
        )
        changed_stories = _extract_story_changes(file_change, sha)

        results: list[dict[str, Any]] = []
        for story in changed_stories:
            story_query = build_story_change_query(story)
            results.append(
                {
                    "type": "story",
                    "id": story["id"],
                    "text": story["text"],
                    "change_type": story["change_type"],
                }
            )
            story_results = [
                *get_related_test_cases(story_query, dataset=dataset),
                *get_related_faults(story_query, dataset=dataset),
                *get_impacted_code(story_query, dataset=dataset),
            ]
            if not story_results:
                story_results = [
                    *get_related_test_cases(story_query),
                    *get_related_faults(story_query),
                    *get_impacted_code(story_query),
                ]
            results.extend(prefer_explicit_links(story_results))

        explained_results = _dedupe_records(_attach_explanations(results))
        block = {
            "trigger": "user_story_modified",
            "dataset": dataset,
            "file": filename,
            "results": _dedupe_records(explained_results),
        }
        block["summary_lines"] = _impact_block_lines(block)
        impacted.append(block)

    # De-duplicate globally so the same artifact is returned once per commit,
    # even when multiple modified sources point to it.
    global_seen: set[tuple[str, str]] = set()
    deduped_impacted: list[dict[str, Any]] = []
    for block in impacted:
        unique_results: list[dict[str, Any]] = []
        for result in block.get("results", []):
            key = _record_key(result)
            if key in global_seen:
                continue
            global_seen.add(key)
            unique_results.append(result)
        if not unique_results:
            continue
        block["results"] = unique_results
        block["summary_lines"] = _impact_block_lines(block)
        deduped_impacted.append(block)

    impacted = deduped_impacted

    report_lines = [f"Commit: {sha}", "--------------------------------"]
    for block in impacted:
        report_lines.extend(block.get("summary_lines", []))

    print(
        json.dumps(
            {
                "sha": sha,
                "impact": impacted,
                "human_readable_report": "\n".join(report_lines),
            }
        )
    )


if __name__ == "__main__":
    run_once()
