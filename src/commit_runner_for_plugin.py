import csv
import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

import requests

from src.agents import search_with_explanations
from src.code_watcher import get_latest_commit
from src.config import GITHUB_REPO, GITHUB_TOKEN

CODE_DIR_NAMES = {"code", "src"}
CODE_EXTENSIONS = {".java"}
STORY_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".md"}


def _select_diverse_results(
    results: list[dict[str, Any]],
    explanations: list[dict[str, Any]],
    allowed_types: set[str],
    max_results: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep retrieval ranking but enforce basic type diversity (story/test/fault) when possible."""
    by_id = {str(item.get("id")): item for item in explanations}

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    # First pass: ensure one hit per expected artifact type when available.
    for wanted_type in ("story", "test_case", "fault", "code"):
        if wanted_type not in allowed_types:
            continue
        for item in results:
            rid = str(item.get("id", ""))
            if item.get("type") == wanted_type and rid not in selected_ids:
                selected.append(item)
                selected_ids.add(rid)
                break

    # Second pass: fill remaining slots by original ranking.
    for item in results:
        rid = str(item.get("id", ""))
        if rid in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(rid)
        if len(selected) >= max_results:
            break

    selected = selected[:max_results]
    selected_explanations = [by_id[str(item.get("id", ""))] for item in selected if str(item.get("id", "")) in by_id]
    return selected, selected_explanations


def _trace_with_dataset_fallback(query: str, dataset: str | None, allowed_types: set[str], k: int = 60) -> dict[str, Any]:
    """Run explanation-aware search with dataset filtering and global fallback."""
    trace = search_with_explanations(query, k=k, dataset=dataset)
    filtered_results = _filter_artifact_types(trace["results"], allowed_types)
    filtered_explanations = [item for item in trace["factorized_explanations"] if item.get("type") in allowed_types]
    if filtered_results or not dataset:
        diverse_results, diverse_explanations = _select_diverse_results(
            filtered_results,
            filtered_explanations,
            allowed_types,
            max_results=25,
        )
        return {"results": diverse_results, "factorized_explanations": diverse_explanations}

    fallback = search_with_explanations(query, k=k)
    fallback_results = _filter_artifact_types(fallback["results"], allowed_types)
    fallback_explanations = [item for item in fallback["factorized_explanations"] if item.get("type") in allowed_types]
    diverse_results, diverse_explanations = _select_diverse_results(
        fallback_results,
        fallback_explanations,
        allowed_types,
        max_results=25,
    )
    return {"results": diverse_results, "factorized_explanations": diverse_explanations}


def _attach_evidence_to_results(results: list[dict[str, Any]], explanations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mirror factorized evidence into each result so consumers reading only `results` still get explanations."""
    by_id = {str(item.get("id")): item.get("evidence", {}) for item in explanations}
    enriched: list[dict[str, Any]] = []
    for result in results:
        item = dict(result)
        rid = str(item.get("id", ""))
        item["evidence"] = by_id.get(rid, {})
        enriched.append(item)
    return enriched


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


def _fetch_file_text_at_commit(sha: str, filename: str) -> str:
    """Fallback when GitHub commit API omits `patch` (common for larger diffs)."""
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{sha}/{filename}"
    response = requests.get(raw_url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=20)
    if response.status_code == 200:
        return response.text
    return ""


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
            filename = file_change["filename"]
            patch_text = file_change.get("patch", "")

            # If no patch is returned by API, analyze current file content so we still emit explanations.
            analysis_text = patch_text or _fetch_file_text_at_commit(sha, filename)
            if not analysis_text:
                continue

            trace = _trace_with_dataset_fallback(analysis_text, dataset, {"story", "test_case", "fault"})
            impacted.append(
                {
                    "trigger": "code_class_modified",
                    "dataset": dataset,
                    "file": filename,
                    "results": _attach_evidence_to_results(trace["results"], trace["factorized_explanations"]),
                    "factorized_explanations": trace["factorized_explanations"],
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
        factorized_explanations: list[dict[str, Any]] = []
        for story in changed_stories:
            results.append({"type": "story", "id": story["id"], "text": story["text"], "evidence": {}})

            trace = _trace_with_dataset_fallback(story["text"], dataset, {"test_case", "fault", "code"})
            story_results = _attach_evidence_to_results(trace["results"], trace["factorized_explanations"])
            results.extend(story_results)
            factorized_explanations.extend(trace["factorized_explanations"])

        impacted.append(
            {
                "trigger": "user_story_modified",
                "dataset": dataset,
                "file": filename,
                "results": results,
                "factorized_explanations": factorized_explanations,
            }
        )

    print(json.dumps({"sha": sha, "impact": impacted}))


if __name__ == "__main__":
    run_once()
