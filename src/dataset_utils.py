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
