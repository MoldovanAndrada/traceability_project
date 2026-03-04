import csv
import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases, search
from src.code_watcher import get_latest_commit
from src.explainability import format_explanation

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


def _attach_explanations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a human-readable explanation to every retrieved artifact result."""
    explained: list[dict[str, Any]] = []
    for record in records:
        enriched = dict(record)
        if enriched.get("type") == "story":
            story_text = (enriched.get("text") or "").strip()
            enriched["explanation_reason"] = (
                f"story changed in commit; text snippet='{story_text[:80]}'"
                if story_text
                else "story changed in commit"
            )
        explanation = format_explanation(enriched)
        # Keep explanation in multiple aliases because downstream plugin clients
        # may read different keys ("reason", "why", "explanation").
        enriched["explanation"] = explanation
        # Common misspelling kept for backward/consumer compatibility.
        enriched["explaination"] = explanation
        enriched["reason"] = explanation
        enriched["why"] = explanation
        explained.append(enriched)
    return explained


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

        explained_results = _attach_explanations(results)
        block = {
            "trigger": "user_story_modified",
            "dataset": dataset,
            "file": filename,
            "results": explained_results,
        }
        block["summary_lines"] = _impact_block_lines(block)
        impacted.append(block)

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
