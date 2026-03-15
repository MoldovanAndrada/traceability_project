import csv
import re
import xml.etree.ElementTree as ET
import zipfile
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
    "dataset-api": {
        "stories": "devfile_api_user_stories_and_requirements.xlsx",
        "tests": "devfile_api_test_cases.xlsx",
        "faults": "devfile_api_faults_remapped.xlsx",
        "code_dir": "src",
        "code_globs": ["*.go"],
    },
    "dataset-app-frontend": {
        "stories": "altinn_app_frontend_react_user_stories.csv",
        "tests": "altinn_app_frontend_react_test_cases.csv",
        "faults": "altinn_app_frontend_react_faults_populated.xlsx",
        "code_dirs": ["app-react-frontend", "app-react-frontend/src", "app-react-content/src"],
        "code_globs": ["*.ts", "*.tsx", "*.css"],
    },
}


def _iter_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    if csv_path.suffix.lower() == ".xlsx":
        yield from _iter_rows_xlsx(csv_path)
        return

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

            target = relmap[rid]
            target_name = target.split("/worksheets/")[-1].split("/")[-1]
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


def _xlsx_row_values(
    row_xml: ET.Element,
    ns: dict[str, str],
    shared_strings: list[str],
) -> list[str]:
    values_by_index: dict[int, str] = {}
    max_index = -1

    for cell in row_xml.findall("a:c", ns):
        cell_ref = cell.attrib.get("r", "")
        match = _CELL_REF.match(cell_ref)
        if match:
            cell_index = _excel_col_to_index(match.group(1))
        else:
            cell_index = max_index + 1

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
        if cell_index > max_index:
            max_index = cell_index

    if max_index < 0:
        return []

    return [values_by_index.get(i, "") for i in range(max_index + 1)]


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
