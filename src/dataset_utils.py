import csv


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
