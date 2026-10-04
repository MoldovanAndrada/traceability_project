import csv
from pathlib import PurePosixPath
from typing import Any, Collection


def dataset_from_path(
    filename: str, dataset_names: Collection[str] | None = None
) -> str | None:
    """Return the dataset directory represented by a repository path."""
    path = PurePosixPath(filename)
    if dataset_names is not None:
        # Longest-first also supports a dataset configured below another
        # dataset directory without relying on naming conventions.
        for dataset in sorted(dataset_names, key=len, reverse=True):
            dataset_path = PurePosixPath(dataset)
            if path.parts[:len(dataset_path.parts)] == dataset_path.parts:
                return dataset
        return None

    # Backward-compatible behavior for callers that do not have a dataset
    # registry. The commit runner always supplies its ingestion registry.
    if path.parts:
        first = path.parts[0]
        if first.startswith("traceability_") or first.startswith(("dataset-", "dataset ")):
            return first
    return None


def build_story_change_query(story: dict[str, str]) -> str:
    """Build a retrieval query that retains the changed story's identity.

    The feature sentence alone is not enough to follow explicit traceability
    links: test cases normally point to the story ID (for example ``US-13``),
    not to an exact copy of its prose.
    """
    return " | ".join(
        value.strip()
        for value in (story.get("id", ""), story.get("text", ""))
        if value and value.strip()
    )


def prefer_explicit_links(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain both authoritative and inferred impact candidates.

    An explicit trace is useful evidence and is ranked first by the search
    pipeline, but it must not suppress other candidates of the same artifact
    type. Those inferred candidates are the potential indirect impact that the
    commit analysis is intended to expose.
    """
    return records


def extract_story_changes_from_patch(patch_text: str) -> list[dict[str, str]]:
    """Return story rows added or removed by a unified diff.

    An edit normally appears as a deletion followed by an addition.  Keying the
    rows by story ID lets the added version win while still preserving rows
    from deletion-only commits.
    """
    changed_by_id: dict[str, dict[str, str]] = {}

    for line in patch_text.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue

        change_type = "added" if line[0] == "+" else "deleted"
        row = next(csv.reader([line[1:]]), None)
        if not row:
            continue

        cells = [cell.strip() for cell in row]
        if not any(cells):
            continue

        story_id = cells[0] or str(len(changed_by_id) + 1)
        story_text = cells[1] if len(cells) > 1 else cells[0]

        existing = changed_by_id.get(story_id)
        if existing is None or change_type == "added":
            changed_by_id[story_id] = {
                "id": story_id,
                "text": story_text,
                "change_type": change_type,
            }

    return list(changed_by_id.values())
