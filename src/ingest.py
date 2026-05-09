import csv
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

BASE = Path(__file__).resolve().parent.parent
EMBEDDINGS_DIR = BASE / "embeddings"
SANITY_SUMMARY_PATH = EMBEDDINGS_DIR / "corpus_sanity_summary.json"

SMALL_BENCHMARK_DATASETS = (
    "traceability_lang",
    "traceability_math_large - corect final",
    "traceability_time_poc_complex",
)

DATASET_CONFIG = {
    "traceability_lang": {
        "stories": "user_stories.csv",
        "tests": "test_cases.csv",
        "faults": "faults.csv",
        "code_dir": "code",
    },
    "traceability_math_large - corect final": {
        "stories": "user_stories.csv",
        "tests": "test_cases.csv",
        "faults": "faults.csv",
        "code_dir": "src",
    },
    "traceability_time_poc_complex": {
        "stories": "time_usr_stories.csv",
        "tests": "test_cases_time.csv",
        "faults": "faults_time.csv",
        "code_dir": "src",
    },
}


def _iter_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    if csv_path.suffix.lower() == ".xlsx":
        yield from _iter_rows_xlsx(csv_path)
        return

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        first_line = handle.readline()
        rest_sample = handle.read(4096)
        handle.seek(0)
        delimiter = "\t" if "\t" in first_line else ","
        if delimiter == "," and "\t" in rest_sample and rest_sample.count("\t") > rest_sample.count(","):
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


_CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def _excel_col_to_index(col: str) -> int:
    idx = 0
    for char in col:
        idx = idx * 26 + (ord(char) - ord("A") + 1)
    return idx - 1


def _iter_rows_xlsx(xlsx_path: Path) -> Iterable[dict[str, str]]:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    with zipfile.ZipFile(xlsx_path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in shared_root.findall("a:si", ns):
                chunks = [node.text or "" for node in si.findall(".//a:t", ns)]
                shared_strings.append("".join(chunks))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}

        for sheet in workbook.findall("a:sheets/a:sheet", ns):
            rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            if rid not in relmap:
                continue

            target_name = relmap[rid].split("/worksheets/")[-1].split("/")[-1]
            xml_path = f"xl/worksheets/{target_name}"
            if xml_path not in archive.namelist():
                continue

            sheet_xml = ET.fromstring(archive.read(xml_path))
            rows = sheet_xml.findall("a:sheetData/a:row", ns)
            if not rows:
                continue

            headers = _xlsx_row_values(rows[0], ns, shared_strings)
            if not headers:
                continue

            for row_xml in rows[1:]:
                values = _xlsx_row_values(row_xml, ns, shared_strings)
                row = {
                    header.strip(): values[idx].strip() if idx < len(values) else ""
                    for idx, header in enumerate(headers)
                    if header.strip()
                }
                if any(row.values()):
                    yield row


def _xlsx_row_values(row_xml: ET.Element, ns: dict[str, str], shared_strings: list[str]) -> list[str]:
    values_by_index: dict[int, str] = {}
    max_index = -1

    for cell in row_xml.findall("a:c", ns):
        cell_ref = cell.attrib.get("r", "")
        match = _CELL_REF.match(cell_ref)
        cell_index = _excel_col_to_index(match.group(1)) if match else max_index + 1

        inline = cell.find("a:is/a:t", ns)
        if inline is not None:
            value = inline.text or ""
        else:
            raw = cell.find("a:v", ns)
            if raw is None:
                value = ""
            elif cell.attrib.get("t") == "s":
                idx = int(raw.text or 0)
                value = shared_strings[idx] if idx < len(shared_strings) else ""
            else:
                value = raw.text or ""

        values_by_index[cell_index] = value
        max_index = max(max_index, cell_index)

    if max_index < 0:
        return []
    return [values_by_index.get(i, "") for i in range(max_index + 1)]


def _join_parts(*parts: str) -> str:
    return " | ".join(part for part in parts if part)


def _build_story_text(row: dict[str, str]) -> str:
    return _join_parts(row.get("user_story_id", ""), row.get("feature_sentence", ""), row.get("documentation_text", ""))


def _build_test_text(row: dict[str, str]) -> str:
    return _join_parts(
        row.get("test_case_id", ""),
        row.get("test_case_title", ""),
        row.get("user_story_id", ""),
        row.get("test_case_steps", ""),
        row.get("expected_behavior", ""),
    )


def _build_fault_text(row: dict[str, str]) -> str:
    return _join_parts(
        row.get("bug_id", ""),
        row.get("related_story", ""),
        row.get("file_path", ""),
        row.get("description", ""),
        row.get("buggy_code", ""),
        row.get("fixed_code", ""),
    )


def _ingest_dataset(dataset_name: str, cfg: dict[str, str]) -> list[dict[str, str]]:
    root = BASE / dataset_name
    records: list[dict[str, str]] = []

    story_path = root / cfg["stories"]
    if story_path.exists():
        for row in _iter_rows(story_path):
            sid = row.get("user_story_id") or f"story-{len(records)}"
            records.append({
                "dataset": dataset_name,
                "type": "story",
                "artifact_subtype": "user_story",
                "id": sid,
                "source": str(story_path.relative_to(BASE)),
                "file_name": story_path.name,
                "text": _build_story_text(row),
            })

    tests_path = root / cfg["tests"]
    if tests_path.exists():
        for row in _iter_rows(tests_path):
            tid = row.get("test_case_id") or f"test-{len(records)}"
            records.append({
                "dataset": dataset_name,
                "type": "test_case",
                "artifact_subtype": "test_case",
                "id": tid,
                "source": str(tests_path.relative_to(BASE)),
                "file_name": tests_path.name,
                "text": _build_test_text(row),
            })

    faults_path = root / cfg["faults"]
    if faults_path.exists():
        for row in _iter_rows(faults_path):
            bid = row.get("bug_id") or f"fault-{len(records)}"
            records.append({
                "dataset": dataset_name,
                "type": "fault",
                "artifact_subtype": "fault",
                "id": bid,
                "source": str(faults_path.relative_to(BASE)),
                "file_name": faults_path.name,
                "path": row.get("file_path", ""),
                "text": _build_fault_text(row),
            })

    code_dirs = cfg.get("code_dirs") or [cfg["code_dir"]]
    code_globs = cfg.get("code_globs", ["*.java"])
    seen: set[Path] = set()

    for code_dir_name in code_dirs:
        code_dir = root / code_dir_name
        if not code_dir.exists():
            continue
        for pattern in code_globs:
            for file_path in sorted(code_dir.rglob(pattern)):
                if file_path in seen:
                    continue
                seen.add(file_path)
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="latin-1", errors="ignore")
                rel_path = str(file_path.relative_to(BASE))
                records.append({
                    "dataset": dataset_name,
                    "type": "code",
                    "artifact_subtype": file_path.suffix.lstrip(".") or "source",
                    "id": rel_path,
                    "path": rel_path,
                    "source": rel_path,
                    "file_name": file_path.name,
                    "text": f"{rel_path}\n{content}",
                })

    return records


def ingest_all() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for dataset_name in SMALL_BENCHMARK_DATASETS:
        records.extend(_ingest_dataset(dataset_name, DATASET_CONFIG[dataset_name]))
    return records


def validate_records(records: list[dict[str, str]]) -> None:
    invalid = [record for record in records if not all(str(record.get(k, "")).strip() for k in ("dataset", "type", "id", "text"))]
    if invalid:
        raise ValueError(f"Found {len(invalid)} records missing dataset/type/id/text")
    datasets = {record["dataset"] for record in records}
    unexpected = datasets.difference(SMALL_BENCHMARK_DATASETS)
    if unexpected:
        raise ValueError(f"Unexpected datasets in small benchmark corpus: {sorted(unexpected)}")


def corpus_sanity(records: list[dict[str, str]], samples_per_dataset: int = 5) -> dict[str, object]:
    by_dataset = Counter(record.get("dataset", "<missing>") for record in records)
    by_type = Counter(record.get("type", "<missing>") for record in records)
    by_dataset_type: dict[str, Counter[str]] = defaultdict(Counter)
    samples: dict[str, list[dict[str, str]]] = {dataset: [] for dataset in SMALL_BENCHMARK_DATASETS}

    for record in records:
        dataset = record.get("dataset", "<missing>")
        artifact_type = record.get("type", "<missing>")
        by_dataset_type[dataset][artifact_type] += 1
        if dataset in samples and len(samples[dataset]) < samples_per_dataset:
            preview = " ".join(str(record.get("text", "")).split())[:160]
            samples[dataset].append({
                "dataset": dataset,
                "type": artifact_type,
                "id": str(record.get("id", "")),
                "text_preview": preview,
            })

    summary = {
        "total_records": len(records),
        "counts_per_dataset": {dataset: int(by_dataset.get(dataset, 0)) for dataset in SMALL_BENCHMARK_DATASETS},
        "counts_per_artifact_type": {artifact_type: int(count) for artifact_type, count in sorted(by_type.items())},
        "counts_per_dataset_and_type": {
            dataset: {artifact_type: int(by_dataset_type[dataset].get(artifact_type, 0)) for artifact_type in sorted(by_type)}
            for dataset in SMALL_BENCHMARK_DATASETS
        },
        "sample_records": samples,
        "target_datasets_only": sorted(by_dataset) == sorted(SMALL_BENCHMARK_DATASETS),
        "required_fields_populated": all(
            all(str(record.get(k, "")).strip() for k in ("dataset", "type", "id", "text")) for record in records
        ),
        "dataset_filter_ready": all(int(by_dataset.get(dataset, 0)) > 0 for dataset in SMALL_BENCHMARK_DATASETS),
    }
    return summary


def print_corpus_sanity(records: list[dict[str, str]]) -> dict[str, object]:
    summary = corpus_sanity(records)
    print("Corpus sanity summary")
    print(f"Total records: {summary['total_records']}")
    print("Counts per dataset:")
    for dataset, count in summary["counts_per_dataset"].items():
        print(f"  {dataset}: {count}")
    print("Counts per artifact type:")
    for artifact_type, count in summary["counts_per_artifact_type"].items():
        print(f"  {artifact_type}: {count}")
    print("Counts per dataset × artifact type:")
    for dataset, type_counts in summary["counts_per_dataset_and_type"].items():
        print(f"  {dataset}: {type_counts}")
    print("Sample records:")
    for dataset, samples in summary["sample_records"].items():
        print(f"  {dataset}:")
        for sample in samples:
            print(f"    [{sample['type']}] {sample['id']}: {sample['text_preview']}")
    print(f"Target datasets only: {summary['target_datasets_only']}")
    print(f"Required fields populated: {summary['required_fields_populated']}")
    print(f"Dataset filter ready: {summary['dataset_filter_ready']}")
    return summary


def save_corpus_sanity(records: list[dict[str, str]], output_path: Path = SANITY_SUMMARY_PATH) -> dict[str, object]:
    summary = corpus_sanity(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
