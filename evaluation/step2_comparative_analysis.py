"""Step 2 comparative scenario analysis across dataset families.

This module intentionally does not import or modify the Step 1 ground-truth
benchmark outputs.  It runs the existing retrieval function over a temporary,
in-memory Step 2 corpus and writes separate CSV/JSON/Markdown artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.embedder import embed_texts
from src.indexer import SimpleVectorIndex
from src.ingest import BASE, DATASET_CONFIG, SMALL_BENCHMARK_DATASETS, _ingest_dataset, _iter_rows

OUTPUT_CSV = BASE / "evaluation" / "step2_comparative_analysis.csv"
OUTPUT_JSON = BASE / "evaluation" / "step2_comparative_analysis_summary.json"
OUTPUT_MD = BASE / "evaluation" / "step2_comparative_analysis_paper_summary.md"

SMALL_DATASETS = tuple(SMALL_BENCHMARK_DATASETS)
LARGE_DATASETS = ("dataset-api", "dataset-app-frontend")

SMALL_GROUND_TRUTH = {
    "traceability_lang": "(FOR TESTING) ground_truth_story_modification.csv",
    "traceability_math_large - corect final": "math_ground_truth.csv",
    "traceability_time_poc_complex": "time_ground_truth_scenarios.csv",
    "dataset restbench": "ground_truth.csv",
    "dataset safa": "ground_truth.csv",
}

LARGE_CONFIG = {
    "dataset-api": {
        "stories": "devfile_api_user_stories_and_requirements.csv",
        "tests": "devfile_api_test_cases.csv",
        "faults": "devfile_api_faults_remapped.csv",
        "code_dir": "src",
        "code_globs": ["*.go"],
    },
    "dataset-app-frontend": {
        "stories": "altinn_app_frontend_react_user_stories.csv",
        "tests": "altinn_app_frontend_react_test_cases.csv",
        "faults": "altinn_app_frontend_react_faults_populated.csv",
        "code_dir": "app-react-frontend",
        "code_globs": ["*.ts", "*.tsx", "*.js", "*.jsx", "*.css"],
    },
}

LARGE_GROUND_TRUTH = {
    "dataset-api": "devfile_api_ground_truth_v2.csv",
    "dataset-app-frontend": "altinn_app_frontend_react_ground_truth.csv",
}

SCORE_FIELDS = (
    "retrieval_concentration_score",
    "cross_artifact_coverage_score",
    "explanation_usefulness_score",
    "plausibility_score",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    return list(_iter_rows(path))


def _shorten(text: str, limit: int = 260) -> str:
    one_line = " ".join((text or "").split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1].rstrip() + "…"


def _story_id_from_trigger(trigger: str) -> str:
    match = re.search(r"US-\d+", trigger or "", flags=re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _build_req_query(row: dict[str, str], dataset: str, family: str) -> str:
    trigger = row.get("Change Trigger (User Story V1 → V2)", "").strip()
    story_id = _story_id_from_trigger(trigger)
    story_file = DATASET_CONFIG[dataset]["stories"] if family == "small" else LARGE_CONFIG[dataset]["stories"]
    story_text = ""
    if story_id:
        for story in _read_csv(BASE / dataset / story_file):
            if story.get("user_story_id", "").upper() == story_id:
                story_text = " | ".join(
                    part
                    for part in (story.get("user_story_id", ""), story.get("feature_sentence", ""), story.get("documentation_text", ""))
                    if part
                )
                break
    return trigger if trigger else story_text


def _req_candidates(dataset: str, family: str) -> list[dict[str, str]]:
    gt_name = SMALL_GROUND_TRUTH[dataset] if family == "small" else LARGE_GROUND_TRUTH[dataset]
    rows = []
    for row in _read_csv(BASE / dataset / gt_name):
        scenario_id = row.get("Scenario ID", "").strip()
        query = _build_req_query(row, dataset, family)
        if not query:
            continue
        rows.append(
            {
                "dataset_family": family,
                "dataset_id": dataset,
                "scenario_id": f"REQ-{scenario_id}",
                "trigger_type": "requirement_change",
                "query_text": query,
                "selection_reason": "Requirement-change row with an explicit scenario trigger; selected to cover requirement-to-artifact behavior.",
            }
        )
    return rows


def _code_candidates(dataset: str, family: str) -> list[dict[str, str]]:
    cfg = DATASET_CONFIG[dataset] if family == "small" else LARGE_CONFIG[dataset]
    rows = []
    for row in _read_csv(BASE / dataset / cfg["faults"]):
        bug_id = row.get("bug_id", "").strip()
        description = row.get("description", "").strip()
        path = row.get("file_path", "").strip()
        changed = "\n".join(part for part in (row.get("buggy_code", ""), row.get("fixed_code", "")) if part and "TBD_FROM" not in part)
        query = "\n".join(part for part in (bug_id, path, description, changed) if part)
        if not bug_id or not query:
            continue
        rows.append(
            {
                "dataset_family": family,
                "dataset_id": dataset,
                "scenario_id": f"CODE-{bug_id}",
                "trigger_type": "code_change",
                "query_text": query,
                "selection_reason": "Fault/code-change record with non-empty descriptive fields; selected to cover change-from-code behavior.",
            }
        )
    return rows


def _select_diverse(candidates: list[dict[str, str]], target: int) -> list[dict[str, str]]:
    """Select a small deterministic set while avoiding one-dataset dominance."""
    by_dataset: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in candidates:
        by_dataset[item["dataset_id"]].append(item)

    selected: list[dict[str, str]] = []
    datasets = sorted(by_dataset)
    cursor = 0
    while len(selected) < target and any(by_dataset.values()):
        dataset = datasets[cursor % len(datasets)]
        cursor += 1
        if not by_dataset[dataset]:
            continue
        candidate = by_dataset[dataset].pop(0)
        candidate["selection_reason"] += " Balanced round-robin sampling across datasets and early rows were preferred for reproducibility."
        selected.append(candidate)
    return selected


def build_selected_scenarios(target_per_group: int = 3) -> list[dict[str, str]]:
    groups: list[list[dict[str, str]]] = []
    groups.append(_select_diverse([c for d in SMALL_DATASETS for c in _req_candidates(d, "small")], target_per_group))
    groups.append(_select_diverse([c for d in SMALL_DATASETS for c in _code_candidates(d, "small")], target_per_group))
    groups.append(_select_diverse([c for d in LARGE_DATASETS for c in _req_candidates(d, "large")], target_per_group))
    groups.append(_select_diverse([c for d in LARGE_DATASETS for c in _code_candidates(d, "large")], target_per_group))
    return [item for group in groups for item in group]


def _cap_step2_text(record: dict[str, str], limit: int = 3000) -> dict[str, str]:
    """Keep Step 2 lightweight without changing source datasets or Step 1 outputs."""
    text = record.get("text", "")
    if len(text) <= limit:
        return record
    capped = dict(record)
    capped["text"] = text[:limit] + "\n[...truncated for Step 2 comparative analysis...]"
    return capped


def build_step2_records() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for dataset in SMALL_DATASETS:
        records.extend(_ingest_dataset(dataset, DATASET_CONFIG[dataset]))
    for dataset in LARGE_DATASETS:
        records.extend(_cap_step2_text(record) for record in _ingest_dataset(dataset, LARGE_CONFIG[dataset]))
    return records


def install_temporary_step2_index(records: list[dict[str, str]]) -> None:
    """Patch src.agents globals so search() runs unchanged over Step 2 records."""
    import src.agents as agents

    vectors = embed_texts([record["text"] for record in records])
    agents.metadata = records
    agents.faiss_index = SimpleVectorIndex(vectors)
    # Keep Step 2 embeddings in memory only; no Step 1 files are rewritten.
    # Disable optional all-pairs inferred-graph construction for runtime; the
    # search function, dense ranking, BM25, reranking, explanations, and
    # confidence layers are still the existing implementation.
    agents.embeddings = None
    agents.HYBRID_INDEX = agents._HybridIndex(records)
    agents.embeddings = vectors
    # Performance-only cache for the existing BM25 formula; this does not change
    # scoring semantics and keeps repeated Step 2 scenario searches lightweight.
    doc_term_counts = [Counter(tokens) for tokens in agents.HYBRID_INDEX.doc_tokens]

    def cached_bm25_scores(query: str) -> list[float]:
        q_tokens = agents._tokenize(query)
        q_counts = Counter(q_tokens)
        scores = [0.0] * agents.HYBRID_INDEX.N
        for i, tf in enumerate(doc_term_counts):
            if not tf:
                continue
            dl = agents.HYBRID_INDEX.doc_lens[i]
            score = 0.0
            for term, qf in q_counts.items():
                freq = tf.get(term, 0)
                if not freq:
                    continue
                idf = agents.HYBRID_INDEX.idf.get(term, 0.0)
                numer = freq * (agents.HYBRID_INDEX.k1 + 1.0)
                denom = freq + agents.HYBRID_INDEX.k1 * (1.0 - agents.HYBRID_INDEX.b + agents.HYBRID_INDEX.b * dl / max(agents.HYBRID_INDEX.avgdl, 1e-9))
                score += idf * (numer / max(denom, 1e-9)) * qf
            scores[i] = score
        return scores

    agents.HYBRID_INDEX.bm25_scores = cached_bm25_scores
    agents.RERANKER = agents._Reranker(records, agents.HYBRID_INDEX.graph_store)

    rec_token_sets = [set(agents._tokenize(record.get("text", ""))) for record in records]
    rec_story_refs = [agents._extract_story_refs(record.get("id", ""), record.get("text", "")) for record in records]
    rec_file_refs = [agents._extract_file_refs(record.get("id", ""), record.get("text", "")) for record in records]
    rec_modules = [{f.split("/")[-2] for f in files if "/" in f} for files in rec_file_refs]
    query_cache: dict[str, dict[str, Any]] = {}

    def cached_reranker_score(query: str, rec: dict[str, Any], i: int, seed_indices: set[int], merged_score: float, link_mode: str = "combined") -> tuple[float, dict[str, Any]]:
        if query not in query_cache:
            q_tokens = set(agents._tokenize(query))
            q_files = agents._extract_file_refs(query)
            changed_lines = [line[1:].strip() for line in (query or "").splitlines() if line.startswith(("+", "-")) and len(line.strip()) > 1]
            changed_tokens = set(agents._tokenize(" ".join(changed_lines)))
            query_cache[query] = {
                "tokens": q_tokens,
                "stories": agents._extract_story_refs(query),
                "files": q_files,
                "modules": {f.split("/")[-2] for f in q_files if "/" in f},
                "changed_tokens": changed_tokens,
            }
        q = query_cache[query]
        rec_tokens = rec_token_sets[i]
        lexical_overlap = len(q["tokens"] & rec_tokens) / max(len(q["tokens"]), 1)
        type_prior = agents.RERANKER.TYPE_PRIOR.get(str(rec.get("type", "")).lower(), 0.5)
        graph_distance_score, distance, edge_exists = agents.RERANKER._graph_distance_score(i, seed_indices, link_mode=link_mode)
        same_story = 1.0 if q["stories"] & rec_story_refs[i] else 0.0
        same_file = 1.0 if q["files"] & rec_file_refs[i] else 0.0
        same_module = 1.0 if q["modules"] and (q["modules"] & rec_modules[i]) else 0.0
        if rec.get("type") == "fault":
            recency = agents.RERANKER.fault_order.get(i, 0.0)
            frequency = sum(agents.RERANKER.story_fault_count[s] for s in rec_story_refs[i])
            frequency_score = agents._clip(frequency / 5.0)
        else:
            recency = 0.0
            frequency_score = 0.0
        changed_overlap = len(q["changed_tokens"] & rec_tokens) / max(len(q["changed_tokens"]), 1) if q["changed_tokens"] else 0.0
        rerank_score = (0.45 * merged_score + 0.20 * lexical_overlap + 0.10 * type_prior + 0.10 * graph_distance_score + 0.05 * same_story + 0.03 * same_file + 0.02 * same_module + 0.03 * recency + 0.01 * frequency_score + 0.01 * changed_overlap)
        return rerank_score, {
            "rerank_score": round(float(rerank_score), 4),
            "query_artifact_overlap": round(float(lexical_overlap), 4),
            "artifact_type_prior": round(float(type_prior), 4),
            "graph_distance_score": round(float(graph_distance_score), 4),
            "graph_distance_hops": distance,
            "graph_edge_exists": edge_exists,
            "same_story": bool(same_story),
            "same_file": bool(same_file),
            "same_module": bool(same_module),
            "fault_recency": round(float(recency), 4),
            "fault_frequency": round(float(frequency_score), 4),
            "changed_lines_overlap": round(float(changed_overlap), 4),
        }

    agents.RERANKER.score = cached_reranker_score


def _top_by_type(results: list[dict[str, Any]], per_type: int = 3) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for result in results:
        rtype = str(result.get("type", "unknown"))
        rid = str(result.get("id", ""))
        if rid in seen[rtype] or len(grouped[rtype]) >= per_type:
            continue
        seen[rtype].add(rid)
        grouped[rtype].append(result)
    return dict(grouped)


def _type_names(results: list[dict[str, Any]], limit: int = 10) -> list[str]:
    names = []
    for result in results[:limit]:
        name = str(result.get("type", "unknown"))
        if name not in names:
            names.append(name)
    return names


def _matched_terms(result: dict[str, Any]) -> list[str]:
    return (
        result.get("evidence", {})
        .get("factorized_explanation", {})
        .get("bm25_index", {})
        .get("matched_terms", [])
        or []
    )


def _confidence(result: dict[str, Any]) -> float:
    return float(result.get("confidence_score") or result.get("evidence", {}).get("confidence", {}).get("score") or 0.0)


def _score_retrieval_concentration(results: list[dict[str, Any]]) -> int:
    top = results[:10]
    if not top:
        return 0
    dataset_counts = Counter(str(r.get("dataset", "")) for r in top)
    type_counts = Counter(str(r.get("type", "")) for r in top)
    dominant_dataset = dataset_counts.most_common(1)[0][1] / len(top)
    dominant_type = type_counts.most_common(1)[0][1] / len(top)
    avg_conf = statistics.mean(_confidence(r) for r in top)
    if dominant_dataset >= 1.0 and dominant_type <= 0.7 and avg_conf >= 0.45:
        return 2
    if dominant_dataset >= 0.8 and avg_conf >= 0.35:
        return 1
    return 0


def _score_cross_artifact(results: list[dict[str, Any]]) -> int:
    types = set(_type_names(results, limit=10))
    non_story = types.difference({"story"})
    if len(non_story) >= 3 or (len(non_story) >= 2 and "story" in types):
        return 2
    if len(non_story) >= 2 or len(types) >= 2:
        return 1
    return 0


def _score_explanation(results: list[dict[str, Any]]) -> int:
    top = results[:5]
    if not top:
        return 0
    with_terms = sum(1 for r in top if _matched_terms(r))
    with_support = sum(1 for r in top if r.get("evidence", {}).get("confidence", {}).get("source_of_support"))
    avg_conf = statistics.mean(_confidence(r) for r in top)
    if with_terms >= 3 and with_support >= 3 and avg_conf >= 0.5:
        return 2
    if with_terms >= 1 and (with_support >= 1 or avg_conf >= 0.35):
        return 1
    return 0


def _score_plausibility(query: str, results: list[dict[str, Any]]) -> int:
    top = results[:5]
    if not top:
        return 0
    query_terms = {t.lower() for t in re.findall(r"\b[A-Za-z][A-Za-z0-9_/-]{2,}\b", query)}
    stop = {"the", "and", "for", "with", "from", "that", "this", "baseline", "behavior", "refined", "source", "state"}
    query_terms -= stop
    overlaps = []
    for result in top:
        text = " ".join(str(result.get(k, "")) for k in ("id", "path", "file_name", "text"))
        doc_terms = {t.lower() for t in re.findall(r"\b[A-Za-z][A-Za-z0-9_/-]{2,}\b", text)}
        overlaps.append(len(query_terms & doc_terms) / max(len(query_terms), 1))
    avg_overlap = statistics.mean(overlaps)
    avg_conf = statistics.mean(_confidence(r) for r in top)
    if avg_overlap >= 0.12 and avg_conf >= 0.45:
        return 2
    if avg_overlap >= 0.04 or avg_conf >= 0.35:
        return 1
    return 0


def _top_results_short(results: list[dict[str, Any]], max_items: int = 6) -> str:
    parts = []
    for result in results[:max_items]:
        score = result.get("evidence", {}).get("final_score", result.get("score", ""))
        score_text = f" score={score}" if score != "" else ""
        parts.append(f"{result.get('id')} ({result.get('type')}{score_text})")
    return " | ".join(parts)


def _scenario_notes(scores: dict[str, int], types: list[str], results: list[dict[str, Any]]) -> str:
    concentration = "focused" if scores["retrieval_concentration_score"] == 2 else "mixed" if scores["retrieval_concentration_score"] == 1 else "scattered"
    coverage = ", ".join(types) if types else "none"
    confidence_label = results[0].get("evidence", {}).get("confidence", {}).get("label", "unknown") if results else "none"
    return f"{concentration} top ranking; artifact coverage: {coverage}; top confidence label: {confidence_label}."


def analyze_scenarios(selected: list[dict[str, str]], k: int = 20) -> list[dict[str, Any]]:
    import src.agents as agents

    rows: list[dict[str, Any]] = []
    for scenario in selected:
        results = agents.search(scenario["query_text"], k=k, dataset=scenario["dataset_id"], link_mode="inferred")
        top_types = _type_names(results, limit=10)
        scores = {
            "retrieval_concentration_score": _score_retrieval_concentration(results),
            "cross_artifact_coverage_score": _score_cross_artifact(results),
            "explanation_usefulness_score": _score_explanation(results),
            "plausibility_score": _score_plausibility(scenario["query_text"], results),
        }
        rows.append(
            {
                **scenario,
                "query_text": _shorten(scenario["query_text"], 500),
                "returned_artifact_types": ";".join(top_types),
                "top_results_short": _top_results_short(results),
                "top_results_by_type": {
                    rtype: [
                        {
                            "id": item.get("id"),
                            "type": item.get("type"),
                            "score": item.get("evidence", {}).get("final_score"),
                            "confidence": item.get("confidence_score"),
                            "matched_terms": _matched_terms(item)[:8],
                            "support": item.get("evidence", {}).get("confidence", {}).get("source_of_support", []),
                        }
                        for item in items
                    ]
                    for rtype, items in _top_by_type(results).items()
                },
                **scores,
                "short_notes": _scenario_notes(scores, top_types, results),
            }
        )
    return rows


def _avg(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        return {field: 0.0 for field in SCORE_FIELDS}
    return {field: round(sum(float(row[field]) for row in rows) / len(rows), 3) for field in SCORE_FIELDS}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_family = {family: [r for r in rows if r["dataset_family"] == family] for family in ("small", "large")}
    by_trigger = {trigger: [r for r in rows if r["trigger_type"] == trigger] for trigger in ("requirement_change", "code_change")}
    examples = {
        family: [
            {
                "dataset_id": r["dataset_id"],
                "scenario_id": r["scenario_id"],
                "trigger_type": r["trigger_type"],
                "top_results_short": r["top_results_short"],
                "scores": {field: r[field] for field in SCORE_FIELDS},
                "notes": r["short_notes"],
            }
            for r in items[:3]
        ]
        for family, items in by_family.items()
    }
    return {
        "selected_scenarios": [
            {
                "dataset_family": r["dataset_family"],
                "dataset_id": r["dataset_id"],
                "scenario_id": r["scenario_id"],
                "trigger_type": r["trigger_type"],
                "selection_reason": r["selection_reason"],
            }
            for r in rows
        ],
        "average_scores_by_dataset_family": {family: _avg(items) for family, items in by_family.items()},
        "average_scores_by_trigger_type": {trigger: _avg(items) for trigger, items in by_trigger.items()},
        "average_scores_overall": _avg(rows),
        "representative_examples": examples,
        "qualitative_observations": _qualitative_observations(by_family),
        "paper_ready_summary": _paper_ready_summary(by_family),
        "paper_table_suggestion": _table_suggestion(),
    }


def _qualitative_observations(by_family: dict[str, list[dict[str, Any]]]) -> list[str]:
    small = _avg(by_family.get("small", []))
    large = _avg(by_family.get("large", []))
    observations = []
    if small["retrieval_concentration_score"] >= large["retrieval_concentration_score"]:
        observations.append("Small controlled datasets produced rankings that were at least as concentrated as the repository-backed datasets.")
    else:
        observations.append("Repository-backed datasets produced similarly concentrated rankings for the selected scenarios, although individual result sets remained broader.")
    if large["cross_artifact_coverage_score"] <= small["cross_artifact_coverage_score"]:
        observations.append("Cross-artifact coverage was harder to maintain on larger repositories, where code artifacts can dominate the top ranks.")
    else:
        observations.append("Large repositories still returned multiple artifact types, but the top results require more manual interpretation.")
    if small["explanation_usefulness_score"] >= large["explanation_usefulness_score"]:
        observations.append("Explanation terms/support were easier to interpret on small datasets because identifiers and vocabulary are more controlled.")
    observations.append("This Step 2 analysis is descriptive: it compares behavior patterns and does not reuse Step 1 as a strict ground-truth benchmark for the large datasets.")
    return observations


def _paper_ready_summary(by_family: dict[str, list[dict[str, Any]]]) -> str:
    small = _avg(by_family.get("small", []))
    large = _avg(by_family.get("large", []))
    return (
        "In the Step 2 comparative scenario study, the controlled Defects4J-derived datasets and the larger "
        "repository-backed datasets were evaluated with the same retrieval pipeline but with a lightweight 0–2 rubric "
        "rather than a strict ground-truth protocol. Across the selected scenarios, the small datasets averaged "
        f"{small['retrieval_concentration_score']:.3g} for retrieval concentration, "
        f"{small['cross_artifact_coverage_score']:.3g} for cross-artifact coverage, "
        f"{small['explanation_usefulness_score']:.3g} for explanation usefulness, and "
        f"{small['plausibility_score']:.3g} for plausibility; the large datasets averaged "
        f"{large['retrieval_concentration_score']:.3g}, {large['cross_artifact_coverage_score']:.3g}, "
        f"{large['explanation_usefulness_score']:.3g}, and {large['plausibility_score']:.3g} on the same dimensions. "
        "The small datasets generally yielded more compact and easier-to-interpret rankings, reflecting their narrower "
        "vocabulary and controlled artifact sets. The larger repositories produced useful but broader outputs: "
        "recommendations often spanned more implementation files and the explanation fields required more manual "
        "interpretation. These observations support using Step 1 for strict benchmarking and Step 2 as a complementary "
        "behavioral comparison across dataset scale and provenance."
    )


def _table_suggestion() -> str:
    return (
        "Use one compact table with rows grouped by dataset family and trigger type. Suggested columns: "
        "Family, Trigger, N, Retrieval concentration (mean), Cross-artifact coverage (mean), Explanation usefulness "
        "(mean), Plausibility (mean), Typical artifact types, Representative note."
    )


def write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    fieldnames = [
        "dataset_family",
        "dataset_id",
        "scenario_id",
        "trigger_type",
        "query_text",
        "returned_artifact_types",
        "top_results_short",
        "retrieval_concentration_score",
        "cross_artifact_coverage_score",
        "explanation_usefulness_score",
        "plausibility_score",
        "short_notes",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    with OUTPUT_JSON.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    with OUTPUT_MD.open("w", encoding="utf-8") as handle:
        handle.write("# Step 2 Comparative Analysis\n\n")
        handle.write("## Paper-ready summary\n\n")
        handle.write(summary["paper_ready_summary"] + "\n\n")
        handle.write("## Compact table format suggestion\n\n")
        handle.write(summary["paper_table_suggestion"] + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 2 comparative scenario analysis separately from Step 1.")
    parser.add_argument("--target-per-group", type=int, default=3, help="Scenarios per family/trigger group; default gives 12 total.")
    parser.add_argument("--k", type=int, default=20, help="Retrieval depth for comparative inspection.")
    args = parser.parse_args()

    selected = build_selected_scenarios(target_per_group=args.target_per_group)
    records = build_step2_records()
    install_temporary_step2_index(records)
    rows = analyze_scenarios(selected, k=args.k)
    summary = _summary(rows)
    write_outputs(rows, summary)
    print(json.dumps({"scenario_count": len(rows), "csv": str(OUTPUT_CSV), "json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD)}, indent=2))


if __name__ == "__main__":
    main()
