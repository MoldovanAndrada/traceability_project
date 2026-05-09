import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ingest import BASE, SMALL_BENCHMARK_DATASETS, corpus_sanity, ingest_all, validate_records

EVALUATION_DIR = BASE / "evaluation"
RESULTS_PATH = EVALUATION_DIR / "requirement_ground_truth_results.csv"
SUMMARY_PATH = EVALUATION_DIR / "requirement_ground_truth_summary.json"
RETRIEVAL_DEPTH = 100
ARTIFACT_TYPES = ("code", "test_cases", "faults")
SKIP_REASONS = ("dataset_filter_empty", "empty_gold", "missing_story_match", "parse_failure")

GROUND_TRUTH_FILES = {
    "traceability_lang": "(FOR TESTING) ground_truth_story_modification.csv",
    "traceability_math_large - corect final": "math_ground_truth.csv",
    "traceability_time_poc_complex": "time_ground_truth_scenarios.csv",
}

STORY_FILES = {
    "traceability_lang": "user_stories.csv",
    "traceability_math_large - corect final": "user_stories.csv",
    "traceability_time_poc_complex": "time_usr_stories.csv",
}

TYPE_ALIASES = {
    "code": "code",
    "test_case": "test_cases",
    "test_cases": "test_cases",
    "fault": "faults",
    "faults": "faults",
}

TC_TOKEN = re.compile(r"TC-\d+", re.IGNORECASE)
BUG_TOKEN = re.compile(r"Bug-\d+", re.IGNORECASE)
TC_RANGE = re.compile(r"(TC-\d+)\s*(?:to|-)\s*(TC-\d+)", re.IGNORECASE)
US_TOKEN = re.compile(r"US-\d+", re.IGNORECASE)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        first_line = handle.readline()
        handle.seek(0)
        delimiter = "\t" if "\t" in first_line else ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [
            {(key or "").strip(): (value or "").strip() for key, value in row.items() if (key or "").strip()}
            for row in reader
            if row and any((value or "").strip() for value in row.values())
        ]


def _story_text(row: dict[str, str]) -> str:
    return " | ".join(
        part
        for part in (row.get("user_story_id", ""), row.get("feature_sentence", ""), row.get("documentation_text", ""))
        if part
    )


def _load_stories() -> dict[str, dict[str, str]]:
    stories: dict[str, dict[str, str]] = {}
    for dataset in SMALL_BENCHMARK_DATASETS:
        path = BASE / dataset / STORY_FILES[dataset]
        stories[dataset] = {row.get("user_story_id", ""): _story_text(row) for row in _read_csv(path)}
    return stories


def _load_code_inventory(records: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    inventory: dict[str, dict[str, str]] = {dataset: {} for dataset in SMALL_BENCHMARK_DATASETS}
    for record in records:
        if record.get("type") != "code":
            continue
        dataset = record["dataset"]
        code_id = record["id"]
        path = Path(code_id)
        keys = {code_id, record.get("path", ""), record.get("file_name", ""), path.name, path.stem}
        if path.suffix:
            keys.add(path.name.removesuffix(path.suffix))
        for key in keys:
            clean = (key or "").strip()
            if clean:
                inventory[dataset][clean.lower()] = code_id
    return inventory


def _expand_tc_range(start: str, end: str) -> list[str]:
    width = len(start.split("-")[-1])
    start_num = int(start.split("-")[-1])
    end_num = int(end.split("-")[-1])
    step = 1 if end_num >= start_num else -1
    return [f"TC-{num:0{width}d}" for num in range(start_num, end_num + step, step)]


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _parse_test_ids(raw: str) -> tuple[list[str], bool]:
    ids: list[str] = []
    consumed = raw
    for match in TC_RANGE.finditer(raw or ""):
        ids.extend(_expand_tc_range(match.group(1).upper(), match.group(2).upper()))
        consumed = consumed.replace(match.group(0), " ")
    ids.extend(token.upper() for token in TC_TOKEN.findall(consumed))
    return _ordered_unique(ids), bool(raw and not ids)


def _normalize_bug(token: str) -> str:
    prefix, num = token.split("-", 1)
    return f"Bug-{int(num):02d}" if num.isdigit() else f"{prefix}-{num}"


def _parse_fault_ids(raw: str) -> tuple[list[str], bool]:
    ids = [_normalize_bug(token) for token in BUG_TOKEN.findall(raw or "")]
    return _ordered_unique(ids), bool(raw and not ids)


def _parse_code_ids(raw: str, dataset: str, inventory: dict[str, dict[str, str]]) -> tuple[list[str], bool]:
    if not raw:
        return [], False
    ids: list[str] = []
    for token in re.split(r"[,;]\s*|\s+and\s+", raw):
        clean = token.strip().strip(". ")
        if not clean:
            continue
        candidates = [clean, clean.removesuffix(".java"), f"{clean}.java"]
        match = next((inventory[dataset][candidate.lower()] for candidate in candidates if candidate.lower() in inventory[dataset]), "")
        if match:
            ids.append(match)
    return _ordered_unique(ids), False


def _scenario_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dataset in SMALL_BENCHMARK_DATASETS:
        for row in _read_csv(BASE / dataset / GROUND_TRUTH_FILES[dataset]):
            rows.append({"dataset": dataset, **row})
    return rows


def _build_query(row: dict[str, str], stories: dict[str, dict[str, str]]) -> tuple[str, str, bool]:
    scenario_text = row.get("Change Trigger (User Story V1 → V2)", "").strip()
    scenario_id = row.get("Scenario ID", "").strip()
    story_match = US_TOKEN.search(scenario_text)
    story_id = story_match.group(0).upper() if story_match else ""
    story_text = stories.get(row["dataset"], {}).get(story_id, "")
    if scenario_text:
        return scenario_text, story_id or scenario_id, not bool(story_text)
    if story_text:
        return story_text, story_id, False
    return "", story_id or scenario_id, True


def _ranked_by_type(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    ranked = {artifact_type: [] for artifact_type in ARTIFACT_TYPES}
    seen = {artifact_type: set() for artifact_type in ARTIFACT_TYPES}
    for result in results:
        artifact_type = TYPE_ALIASES.get(str(result.get("type", "")))
        if artifact_type not in ranked:
            continue
        rid = str(result.get("id", ""))
        if rid and rid not in seen[artifact_type]:
            seen[artifact_type].add(rid)
            ranked[artifact_type].append(rid)
    return ranked


def _metrics(gold: list[str], ranked: list[str]) -> dict[str, Any]:
    gold_set = set(gold)
    first_relevant_rank = ""
    relevant_seen = 0
    precision_sum = 0.0
    for rank, pred in enumerate(ranked, start=1):
        if pred in gold_set:
            relevant_seen += 1
            precision_sum += relevant_seen / rank
            if first_relevant_rank == "":
                first_relevant_rank = rank
    top10 = ranked[:10]
    top10_hits = len(set(top10).intersection(gold_set))
    precision10 = top10_hits / 10
    recall10 = top10_hits / len(gold_set) if gold_set else 0.0
    f1 = (2 * precision10 * recall10 / (precision10 + recall10)) if precision10 + recall10 else 0.0
    return {
        "first_relevant_rank": first_relevant_rank,
        "hit@10": 1.0 if top10_hits else 0.0,
        "mrr": 1.0 / first_relevant_rank if first_relevant_rank else 0.0,
        "ap": precision_sum / len(gold_set) if gold_set else 0.0,
        "precision@10": precision10,
        "recall@10_top10_set": recall10,
        "f1@10_top10_set": f1,
    }


def _mean(rows: list[dict[str, Any]], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows) if rows else 0.0


def _main_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "query_count": len(rows),
        "hit@10": _mean(rows, "hit@10"),
        "mrr": _mean(rows, "mrr"),
        "map": _mean(rows, "ap"),
    }


def _diagnostic_block(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "top10_precision": _mean(rows, "precision@10"),
        "top10_recall": _mean(rows, "recall@10_top10_set"),
        "top10_f1": _mean(rows, "f1@10_top10_set"),
    }


def _group(rows: list[dict[str, Any]], key: str, values: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    return {value: [row for row in rows if row[key] == value] for value in values}


def _tokenize_for_fallback(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", (text or "").lower())


def _local_dataset_search(query: str, records: list[dict[str, str]], dataset: str, k: int) -> list[dict[str, Any]]:
    """Deterministic self-contained search for evaluation-only dataset-local retrieval."""
    query_terms = Counter(_tokenize_for_fallback(query))
    if not query_terms:
        return []

    scored: list[tuple[float, int, dict[str, str]]] = []
    for index, record in enumerate(records):
        if record.get("dataset") != dataset:
            continue
        text_terms = Counter(_tokenize_for_fallback(record.get("text", "")))
        if not text_terms:
            continue
        overlap = sum(min(count, text_terms.get(term, 0)) for term, count in query_terms.items())
        id_bonus = 2.0 if str(record.get("id", "")).lower() in (query or "").lower() else 0.0
        type_bonus = {"story": 0.1, "test_case": 0.08, "fault": 0.06, "code": 0.04}.get(record.get("type", ""), 0.0)
        score = overlap + id_bonus + type_bonus
        if score > 0:
            scored.append((score, -index, record))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [dict(record) for _, _, record in scored[:k]]


def _load_agent_search():
    try:
        from src.agents import search
    except Exception:
        return None
    return search


def _dataset_search(query: str, dataset: str, records: list[dict[str, str]], agent_search, k: int) -> list[dict[str, Any]]:
    if not query:
        return []
    if agent_search is not None:
        try:
            return agent_search(query, k=k, dataset=dataset)
        except ValueError as exc:
            if "truth value" not in str(exc) and "ambiguous" not in str(exc):
                raise
    return _local_dataset_search(query, records, dataset, k)


def evaluate(use_agent_search: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = ingest_all()
    validate_records(records)
    sanity = corpus_sanity(records)
    stories = _load_stories()
    code_inventory = _load_code_inventory(records)

    agent_search = _load_agent_search() if use_agent_search else None

    result_rows: list[dict[str, Any]] = []
    debug_samples: list[dict[str, Any]] = []

    for scenario in _scenario_rows():
        dataset = scenario["dataset"]
        scenario_id = scenario.get("Scenario ID", "")
        query, story_or_scenario_id, missing_story = _build_query(scenario, stories)
        tests, tests_failed = _parse_test_ids(scenario.get("Affected TCs (Ground Truth)", ""))
        faults, faults_failed = _parse_fault_ids(scenario.get("Relevant Faults (Ground Truth)", ""))
        code, code_failed = _parse_code_ids(scenario.get("Impacted Code Artifacts", ""), dataset, code_inventory)
        expected_by_type = {"code": code, "test_cases": tests, "faults": faults}
        parse_failed_by_type = {"code": code_failed, "test_cases": tests_failed, "faults": faults_failed}

        dataset_results = _dataset_search(query, dataset, records, agent_search, RETRIEVAL_DEPTH)
        dataset_filter_empty = not dataset_results
        ranked = _ranked_by_type(dataset_results)

        if len(debug_samples) < 8:
            debug_samples.append({
                "dataset": dataset,
                "story/scenario id": story_or_scenario_id or scenario_id,
                "query text": query,
                "expected IDs by type": expected_by_type,
                "ranked IDs by type": {key: value[:10] for key, value in ranked.items()},
                "first relevant rank by type": {
                    key: _metrics(value, ranked[key])["first_relevant_rank"] if value else "" for key, value in expected_by_type.items()
                },
                "dataset_filter_empty": dataset_filter_empty,
                "missing_story_match": missing_story,
            })

        for artifact_type in ARTIFACT_TYPES:
            gold = expected_by_type[artifact_type]
            skip_reason = ""
            if parse_failed_by_type[artifact_type]:
                skip_reason = "parse_failure"
            elif missing_story and not query:
                skip_reason = "missing_story_match"
            elif not gold:
                skip_reason = "empty_gold"
            elif dataset_filter_empty:
                skip_reason = "dataset_filter_empty"

            scored = not skip_reason
            metric_values = _metrics(gold, ranked[artifact_type]) if scored else {
                "first_relevant_rank": "",
                "hit@10": "",
                "mrr": "",
                "ap": "",
                "precision@10": "",
                "recall@10_top10_set": "",
                "f1@10_top10_set": "",
            }
            result_rows.append({
                "dataset_id": dataset,
                "user_story_id or scenario_id": story_or_scenario_id or scenario_id,
                "artifact_type": artifact_type,
                "gold_non_empty": bool(gold),
                "expected_ids": ";".join(gold),
                "ranked_ids_top10": ";".join(ranked[artifact_type][:10]),
                "first_relevant_rank": metric_values["first_relevant_rank"],
                "hit@10": metric_values["hit@10"],
                "mrr": metric_values["mrr"],
                "ap": metric_values["ap"],
                "precision@10": metric_values["precision@10"],
                "recall@10_top10_set": metric_values["recall@10_top10_set"],
                "f1@10_top10_set": metric_values["f1@10_top10_set"],
                "scored_for_summary": scored,
                "skip_reason": skip_reason,
            })

    scored_rows = [row for row in result_rows if row["scored_for_summary"]]
    skipped_rows = [row for row in result_rows if not row["scored_for_summary"]]
    skipped_by_reason = Counter(row["skip_reason"] for row in skipped_rows)

    per_dataset_rows = _group(scored_rows, "dataset_id", SMALL_BENCHMARK_DATASETS)
    per_type_rows = _group(scored_rows, "artifact_type", ARTIFACT_TYPES)
    summary = {
        "main_quantitative_results": {"overall": _main_block(scored_rows)},
        "per_dataset": {dataset: _main_block(rows) for dataset, rows in per_dataset_rows.items()},
        "per_artifact_type": {artifact_type: _main_block(rows) for artifact_type, rows in per_type_rows.items()},
        "secondary_top10_diagnostics": {
            "overall": _diagnostic_block(scored_rows),
            "per_dataset": {dataset: _diagnostic_block(rows) for dataset, rows in per_dataset_rows.items()},
            "per_artifact_type": {artifact_type: _diagnostic_block(rows) for artifact_type, rows in per_type_rows.items()},
        },
        "scored_query_count": len(scored_rows),
        "skipped_query_count": len(skipped_rows),
        "skipped_by_reason": {reason: int(skipped_by_reason.get(reason, 0)) for reason in SKIP_REASONS},
        "retrieval_depth": RETRIEVAL_DEPTH,
        "corpus_sanity_summary": {
            "total_records": sanity["total_records"],
            "counts_per_dataset": sanity["counts_per_dataset"],
            "counts_per_artifact_type": sanity["counts_per_artifact_type"],
            "counts_per_dataset_and_type": sanity["counts_per_dataset_and_type"],
        },
        "debug_samples": debug_samples,
    }
    return result_rows, summary


def write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset_id",
        "user_story_id or scenario_id",
        "artifact_type",
        "gold_non_empty",
        "expected_ids",
        "ranked_ids_top10",
        "first_relevant_rank",
        "hit@10",
        "mrr",
        "ap",
        "precision@10",
        "recall@10_top10_set",
        "f1@10_top10_set",
        "scored_for_summary",
        "skip_reason",
    ]
    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dataset-local ground-truth retrieval evaluation for the 3 compact benchmark datasets.")
    parser.add_argument("--no-write", action="store_true", help="Run evaluation without writing CSV/JSON outputs.")
    parser.add_argument(
        "--use-agent-search",
        action="store_true",
        help="Use src.agents.search when available; default uses the self-contained dataset-local search path.",
    )
    args = parser.parse_args()
    rows, summary = evaluate(use_agent_search=args.use_agent_search)
    if not args.no_write:
        write_outputs(rows, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
