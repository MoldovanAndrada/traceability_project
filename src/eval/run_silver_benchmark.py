from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from src.agents import search

from .benchmark import build_benchmark_events, write_events_jsonl
from .metrics import TARGET_TYPES, compute_metrics

OUTPUT_DIR = Path("outputs/eval/silver")


def _extract_predictions(query_text: str, dataset_id: str, k: int = 200) -> dict[str, list[str]]:
    ranked = search(query_text, k=k, dataset=dataset_id, link_mode="combined")
    by_type = {target: [] for target in TARGET_TYPES}
    for rec in ranked:
        record_type = str(rec.get("type", "")).lower()
        if record_type in by_type:
            by_type[record_type].append(str(rec.get("id", "")))
    return by_type


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_csv_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _flatten_metrics(metrics: dict, level: str) -> list[dict]:
    rows: list[dict] = []
    if level == "dataset":
        for dataset_id, values in metrics["by_dataset"].items():
            rows.append({"dataset_id": dataset_id, **values})
    elif level == "target_type":
        for target_type, values in metrics["by_target_type"].items():
            rows.append({"target_type": target_type, **values})
    else:
        for dataset_id, by_type in metrics["by_dataset_and_type"].items():
            for target_type, values in by_type.items():
                rows.append({"dataset_id": dataset_id, "target_type": target_type, **values})
    return rows


def run() -> None:
    events = build_benchmark_events()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    benchmark_path = OUTPUT_DIR / "benchmark_events.jsonl"
    write_events_jsonl(events, benchmark_path)

    prediction_records = []
    predictions_by_event: dict[str, dict[str, list[str]]] = {}

    for event in events:
        event_predictions = _extract_predictions(event.query_text, event.dataset_id)
        predictions_by_event[event.event_id] = event_predictions

        prediction_records.append(
            {
                "event_id": event.event_id,
                "dataset_id": event.dataset_id,
                "query_id": event.query_id,
                "trigger_type": event.trigger_type,
                "query_text": event.query_text,
                "gold": event.gold,
                "predictions": event_predictions,
            }
        )

    predictions_path = OUTPUT_DIR / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as handle:
        for record in prediction_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    events_for_metrics = [asdict(event) for event in events]
    metrics = compute_metrics(events_for_metrics, predictions_by_event)

    _write_json(OUTPUT_DIR / "metrics_summary.json", metrics)
    _write_csv_rows(OUTPUT_DIR / "metrics_by_dataset.csv", _flatten_metrics(metrics, "dataset"))
    _write_csv_rows(OUTPUT_DIR / "metrics_by_target_type.csv", _flatten_metrics(metrics, "target_type"))
    _write_csv_rows(
        OUTPUT_DIR / "metrics_by_dataset_and_type.csv",
        _flatten_metrics(metrics, "dataset_and_type"),
    )

    print(f"Wrote {len(events)} story-change benchmark events to {benchmark_path}.")
    print(f"Wrote predictions to {predictions_path}.")
    print(f"Wrote metrics to {OUTPUT_DIR / 'metrics_summary.json'}.")
    print("Usage example:")
    print("  python -m src.eval.run_silver_benchmark")


if __name__ == "__main__":
    run()
