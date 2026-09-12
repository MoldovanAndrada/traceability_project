import csv
from pathlib import PurePosixPath


def dataset_from_path(filename: str) -> str | None:
    """Return the top-level dataset directory for a repository path.

    Dataset repositories historically used either the ``traceability_`` prefix
    or the hyphenated ``dataset-`` prefix. Accept the other common separators
    too so directories such as ``dataset safa`` and ``dataset restbench`` are
    not silently treated as unrelated files.
    """
    parts = PurePosixPath(filename).parts
    if not parts:
        return None

    first = parts[0]
    normalized = first.casefold()
    if normalized.startswith("traceability_") or normalized.startswith(("dataset-", "dataset_", "dataset ")):
        return first
    return None


def extract_story_changes_from_patch(patch_text: str) -> list[dict[str, str]]:
    """Extract added, updated, and deleted story rows from a git patch."""
    changed_by_id: dict[str, dict[str, str]] = {}

    for line in patch_text.splitlines():
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue

        change_type = "added" if line.startswith("+") else "deleted"
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
            story_id, story_text = row[0], row[1]
        else:
            story_id, story_text = str(len(changed_by_id) + 1), row[0]

        existing = changed_by_id.get(story_id)
        # Prefer post-change text when an edit has both deleted and added rows.
        if existing is None or change_type == "added":
            changed_by_id[story_id] = {
                "id": story_id,
                "text": story_text,
                "change_type": change_type,
            }

    return list(changed_by_id.values())
