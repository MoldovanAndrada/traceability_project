from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent

RANGE_PATTERN = re.compile(r"\b(TC|BUG)-?(\d+)\s+to\s+(?:TC|BUG)-?(\d+)\b", re.IGNORECASE)
ID_PATTERN = re.compile(r"\b(TC|BUG)-?(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class DatasetAdapter:
    dataset_id: str
    scenario_file: Path
    scenario_id_col: str
    query_text_col: str
    gold_test_col: str
    gold_fault_col: str
    gold_code_col: str


DATASET_ADAPTERS: list[DatasetAdapter] = [
    DatasetAdapter(
        dataset_id="traceability_lang",
        scenario_file=BASE / "traceability_lang" / "(FOR TESTING) ground_truth_story_modification.csv",
        scenario_id_col="Scenario ID",
        query_text_col="Change Trigger (User Story V1 → V2)",
        gold_test_col="Affected TCs (Ground Truth)",
        gold_fault_col="Relevant Faults (Ground Truth)",
        gold_code_col="Impacted Code Artifacts",
    ),
    DatasetAdapter(
        dataset_id="traceability_math_large - corect final",
        scenario_file=BASE / "traceability_math_large - corect final" / "math_ground_truth.csv",
        scenario_id_col="Scenario ID",
        query_text_col="Change Trigger (User Story V1 → V2)",
        gold_test_col="Affected TCs (Ground Truth)",
        gold_fault_col="Relevant Faults (Ground Truth)",
        gold_code_col="Impacted Code Artifacts",
    ),
    DatasetAdapter(
        dataset_id="traceability_time_poc_complex",
        scenario_file=BASE / "traceability_time_poc_complex" / "time_ground_truth_scenarios.csv",
        scenario_id_col="Scenario ID",
        query_text_col="Change Trigger (User Story V1 → V2)",
        gold_test_col="Affected TCs (Ground Truth)",
        gold_fault_col="Relevant Faults (Ground Truth)",
        gold_code_col="Impacted Code Artifacts",
    ),
]


def iter_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        rows = []
        for row in csv.DictReader(handle, delimiter=delimiter):
            cleaned = {(k or "").strip(): (v or "").strip() for k, v in row.items() if (k or "").strip()}
            if any(cleaned.values()):
                rows.append(cleaned)
        return rows


def normalize_numeric_id(prefix: str, num: int) -> str:
    return f"{prefix.upper()}-{num}"


def parse_id_list(raw: str) -> list[str]:
    if not raw:
        return []

    ids: set[str] = set()
    for m in RANGE_PATTERN.finditer(raw):
        prefix = m.group(1).upper()
        start = int(m.group(2))
        end = int(m.group(3))
        if end >= start:
            for value in range(start, end + 1):
                ids.add(normalize_numeric_id(prefix, value))

    for m in ID_PATTERN.finditer(raw):
        ids.add(normalize_numeric_id(m.group(1), int(m.group(2))))

    return sorted(ids)


def parse_code_list(raw: str) -> list[str]:
    if not raw:
        return []
    values = []
    for part in re.split(r"[,;]", raw):
        item = part.strip()
        if item:
            values.append(item)
    # Deduplicate while preserving order
    deduped = list(dict.fromkeys(values))
    return deduped
