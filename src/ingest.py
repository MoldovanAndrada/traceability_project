import csv
from pathlib import Path
from typing import Iterable

BASE = Path(__file__).resolve().parent.parent

DATASET_CONFIG = {
    "traceability_lang": {
        "stories": "user_stories.csv",
        "tests": "test_cases.csv",
        "faults": "faults.csv",
        "code_dir": "code",
    },
    "traceability_time_poc_complex": {
        "stories": "time_usr_stories.csv",
        "tests": "test_cases_time.csv",
        "faults": "faults_time.csv",
        "code_dir": "src",
    },
    "traceability_math_large - corect final": {
        "stories": "user_stories.csv",
        "tests": "test_cases.csv",
        "faults": "faults.csv",
        "code_dir": "src",
    },
}


def _iter_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)

        delimiter = ","
        if "\t" in sample and sample.count("\t") > sample.count(","):
            delimiter = "\t"

        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            if not row:
                continue
            cleaned = {
                (k or "").strip(): (v or "").strip()
                for k, v in row.items()
                if (k or "").strip()
            }
            if any(cleaned.values()):
                yield cleaned


def _build_story_text(row: dict[str, str]) -> str:
    return " | ".join(
        part
        for part in [
            row.get("user_story_id", ""),
            row.get("feature_sentence", ""),
            row.get("documentation_text", ""),
        ]
        if part
    )


def _build_test_text(row: dict[str, str]) -> str:
    return " | ".join(
        part
        for part in [
            row.get("test_case_id", ""),
            row.get("test_case_title", ""),
            row.get("user_story_id", ""),
            row.get("test_case_steps", ""),
            row.get("expected_behavior", ""),
        ]
        if part
    )


def _build_fault_text(row: dict[str, str]) -> str:
    return " | ".join(
        part
        for part in [
            row.get("bug_id", ""),
            row.get("related_story", ""),
            row.get("file_path", ""),
            row.get("description", ""),
            row.get("buggy_code", ""),
            row.get("fixed_code", ""),
        ]
        if part
    )


def _ingest_dataset(dataset_name: str, cfg: dict[str, str]) -> list[dict[str, str]]:
    root = BASE / dataset_name
    records: list[dict[str, str]] = []

    story_path = root / cfg["stories"]
    if story_path.exists():
        for row in _iter_rows(story_path):
            sid = row.get("user_story_id") or f"story-{len(records)}"
            records.append(
                {
                    "dataset": dataset_name,
                    "type": "story",
                    "id": sid,
                    "source": str(story_path.relative_to(BASE)),
                    "text": _build_story_text(row),
                }
            )

    tests_path = root / cfg["tests"]
    if tests_path.exists():
        for row in _iter_rows(tests_path):
            tid = row.get("test_case_id") or f"test-{len(records)}"
            records.append(
                {
                    "dataset": dataset_name,
                    "type": "test_case",
                    "id": tid,
                    "source": str(tests_path.relative_to(BASE)),
                    "text": _build_test_text(row),
                }
            )

    faults_path = root / cfg["faults"]
    if faults_path.exists():
        for row in _iter_rows(faults_path):
            bid = row.get("bug_id") or f"fault-{len(records)}"
            records.append(
                {
                    "dataset": dataset_name,
                    "type": "fault",
                    "id": bid,
                    "source": str(faults_path.relative_to(BASE)),
                    "path": row.get("file_path", ""),
                    "text": _build_fault_text(row),
                }
            )

    code_dir = root / cfg["code_dir"]
    if code_dir.exists():
        for file_path in sorted(code_dir.rglob("*.java")):
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = file_path.read_text(encoding="latin-1", errors="ignore")

            rel_path = str(file_path.relative_to(BASE))
            records.append(
                {
                    "dataset": dataset_name,
                    "type": "code",
                    "id": rel_path,
                    "path": rel_path,
                    "source": rel_path,
                    "text": f"{rel_path}\n{content}",
                }
            )

    return records


def ingest_all() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for dataset_name, cfg in DATASET_CONFIG.items():
        records.extend(_ingest_dataset(dataset_name, cfg))
    return records
