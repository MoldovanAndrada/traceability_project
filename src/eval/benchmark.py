from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .adapters import BASE, DATASET_ADAPTERS, DatasetAdapter, iter_csv_rows, parse_code_list, parse_id_list


@dataclass(frozen=True)
class BenchmarkEvent:
    event_id: str
    dataset_id: str
    trigger_type: str
    query_text: str
    query_id: str
    gold: dict[str, list[str]]
    source_file: str
    raw_row: dict[str, Any]


def build_benchmark_events(adapters: list[DatasetAdapter] | None = None) -> list[BenchmarkEvent]:
    adapters = adapters or DATASET_ADAPTERS
    events: list[BenchmarkEvent] = []

    for adapter in adapters:
        rows = iter_csv_rows(adapter.scenario_file)
        rel_source = str(adapter.scenario_file.relative_to(BASE))
        for row in rows:
            query_id = (row.get(adapter.scenario_id_col) or "").strip() or str(len(events) + 1)
            query_text = (row.get(adapter.query_text_col) or "").strip()
            if not query_text:
                continue

            event = BenchmarkEvent(
                event_id=f"{adapter.dataset_id}::story_change::{query_id}",
                dataset_id=adapter.dataset_id,
                trigger_type="story_change",
                query_text=query_text,
                query_id=query_id,
                gold={
                    "code": parse_code_list(row.get(adapter.gold_code_col, "")),
                    "test_case": parse_id_list(row.get(adapter.gold_test_col, "")),
                    "fault": parse_id_list(row.get(adapter.gold_fault_col, "")),
                },
                source_file=rel_source,
                raw_row=row,
            )
            events.append(event)

    return events


def write_events_jsonl(events: list[BenchmarkEvent], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
