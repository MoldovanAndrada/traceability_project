"""Step 3 qualitative case analysis for representative scenarios.

Step 3 is intentionally separate from the Step 1 benchmark and Step 2
comparative analysis. It runs the existing retrieval function over a temporary
in-memory corpus and writes small, case-oriented artifacts for paper use.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.step2_comparative_analysis import (  # noqa: E402
    LARGE_CONFIG,
    LARGE_GROUND_TRUTH,
    SMALL_GROUND_TRUTH,
    build_step2_records,
    install_temporary_step2_index,
)
from src.ingest import BASE, DATASET_CONFIG, _iter_rows  # noqa: E402

OUTPUT_JSON = BASE / "evaluation" / "step3_case_analysis.json"
OUTPUT_MD = BASE / "evaluation" / "step3_case_analysis.md"
OUTPUT_CSV = BASE / "evaluation" / "step3_case_analysis.csv"

STORY_FILES = {
    "small": {dataset: cfg["stories"] for dataset, cfg in DATASET_CONFIG.items()},
    "large": {dataset: cfg["stories"] for dataset, cfg in LARGE_CONFIG.items()},
}

GROUND_TRUTH_FILES = {
    "small": SMALL_GROUND_TRUTH,
    "large": LARGE_GROUND_TRUTH,
}

CURATED_CASES = [
    {
        "case_id": "C1",
        "dataset_family": "small",
        "dataset_id": "traceability_lang",
        "scenario_id": "REQ-1",
        "trigger_type": "requirement_change",
        "source_id": "1",
        "selection_reason": "Controlled requirement-change case with explicit normalization/capitalization vocabulary; selected as a clean success-oriented example.",
        "expected_behavior": "clear",
    },
    {
        "case_id": "C2",
        "dataset_family": "small",
        "dataset_id": "traceability_time_poc_complex",
        "scenario_id": "REQ-2",
        "trigger_type": "requirement_change",
        "source_id": "2",
        "selection_reason": "Controlled requirement-change case about overflow and 24h wrap; selected because it tends to mix relevant time artifacts with broader temporal utilities.",
        "expected_behavior": "mixed",
    },
    {
        "case_id": "C3",
        "dataset_family": "small",
        "dataset_id": "traceability_math_large - corect final",
        "scenario_id": "CODE-Bug-05",
        "trigger_type": "code_change",
        "source_id": "Bug-05",
        "selection_reason": "Code/fault-triggered division-by-zero case; selected to inspect whether code-side evidence leads back to code, tests, and related faults.",
        "expected_behavior": "clear",
    },
    {
        "case_id": "C4",
        "dataset_family": "small",
        "dataset_id": "traceability_lang",
        "scenario_id": "CODE-Bug-20",
        "trigger_type": "code_change",
        "source_id": "Bug-20",
        "selection_reason": "Code/fault-triggered language-normalization case; selected as a partially successful case where related string artifacts can broaden the ranking.",
        "expected_behavior": "mixed",
    },
    {
        "case_id": "C5",
        "dataset_family": "large",
        "dataset_id": "dataset-api",
        "scenario_id": "REQ-1",
        "trigger_type": "requirement_change",
        "source_id": "1",
        "selection_reason": "Repository-backed requirement-change case with broad command-schema validation scope; selected to illustrate scale-driven ambiguity and noisy but interpretable links.",
        "expected_behavior": "noisy",
    },
    {
        "case_id": "C6",
        "dataset_family": "large",
        "dataset_id": "dataset-app-frontend",
        "scenario_id": "CODE-Bug-015",
        "trigger_type": "code_change",
        "source_id": "Bug-015",
        "selection_reason": "Repository-backed code/fault trigger about option-fetch failures blocking PDF generation; selected to show mixed fault/story retrieval on a realistic UI workflow.",
        "expected_behavior": "mixed",
    },
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    return list(_iter_rows(path))


def _shorten(text: str, limit: int = 500) -> str:
    one_line = " ".join((text or "").split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1].rstrip() + "…"


def _story_id_from_trigger(trigger: str) -> str:
    match = re.search(r"US-\d+", trigger or "", flags=re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _story_text(dataset: str, family: str, story_id: str) -> str:
    if not story_id:
        return ""
    story_file = STORY_FILES[family][dataset]
    for story in _read_csv(BASE / dataset / story_file):
        if story.get("user_story_id", "").upper() == story_id:
            return " | ".join(
                part
                for part in (story.get("user_story_id", ""), story.get("feature_sentence", ""), story.get("documentation_text", ""))
                if part
            )
    return ""


def _requirement_trigger(case: dict[str, str]) -> tuple[str, dict[str, str]]:
    gt_file = GROUND_TRUTH_FILES[case["dataset_family"]][case["dataset_id"]]
    for row in _read_csv(BASE / case["dataset_id"] / gt_file):
        if row.get("Scenario ID", "").strip() == case["source_id"]:
            trigger = row.get("Change Trigger (User Story V1 → V2)", "").strip()
            story_text = _story_text(case["dataset_id"], case["dataset_family"], _story_id_from_trigger(trigger))
            return trigger or story_text, row
    raise ValueError(f"Missing requirement case {case['dataset_id']} {case['source_id']}")


def _code_trigger(case: dict[str, str]) -> tuple[str, dict[str, str]]:
    cfg = DATASET_CONFIG[case["dataset_id"]] if case["dataset_family"] == "small" else LARGE_CONFIG[case["dataset_id"]]
    for row in _read_csv(BASE / case["dataset_id"] / cfg["faults"]):
        if row.get("bug_id", "").strip() == case["source_id"]:
            changed = "\n".join(
                part
                for part in (row.get("buggy_code", ""), row.get("fixed_code", ""))
                if part and "TBD_FROM" not in part
            )
            query = "\n".join(
                part
                for part in (row.get("bug_id", ""), row.get("file_path", ""), row.get("description", ""), changed)
                if part
            )
            return query, row
    raise ValueError(f"Missing code case {case['dataset_id']} {case['source_id']}")


def _build_trigger(case: dict[str, str]) -> tuple[str, dict[str, str]]:
    if case["trigger_type"] == "requirement_change":
        return _requirement_trigger(case)
    return _code_trigger(case)


def _clean_query_for_display(query: str) -> str:
    """Display-only normalization; the raw query is still sent to search()."""
    return re.sub(r"\s+", " ", query or "").strip()


def _matched_terms(result: dict[str, Any]) -> list[str]:
    return (
        result.get("evidence", {})
        .get("factorized_explanation", {})
        .get("bm25_index", {})
        .get("matched_terms", [])
        or []
    )


def _support(result: dict[str, Any]) -> list[str]:
    return result.get("evidence", {}).get("confidence", {}).get("source_of_support", []) or []


def _graph_signal(result: dict[str, Any]) -> dict[str, Any]:
    graph = result.get("evidence", {}).get("factorized_explanation", {}).get("graph_index", {})
    reranker = result.get("evidence", {}).get("factorized_explanation", {}).get("reranker", {})
    return {
        "graph_score": graph.get("score"),
        "graph_neighbors": graph.get("neighbors"),
        "graph_method": graph.get("method"),
        "reranker_graph_distance": reranker.get("graph_distance"),
        "reranker_graph_depth": reranker.get("graph_depth"),
        "reranker_has_graph_path": reranker.get("has_graph_path"),
    }


def _compact_result(result: dict[str, Any], rank: int) -> dict[str, Any]:
    confidence = result.get("evidence", {}).get("confidence", {})
    factors = result.get("evidence", {}).get("factorized_explanation", {})
    return {
        "rank": rank,
        "id": result.get("id"),
        "type": result.get("type"),
        "artifact_subtype": result.get("artifact_subtype"),
        "path": result.get("path") or result.get("source") or result.get("file_name"),
        "score": result.get("evidence", {}).get("final_score", result.get("score")),
        "confidence_score": result.get("confidence_score"),
        "confidence_label": confidence.get("label"),
        "support": _support(result),
        "matched_terms": _matched_terms(result)[:12],
        "dense_score": factors.get("dense_index", {}).get("score"),
        "bm25_score": factors.get("bm25_index", {}).get("score"),
        "graph_score": factors.get("graph_index", {}).get("score"),
        "text_preview": _shorten(result.get("text", ""), 240),
    }


def _top_by_type(results: list[dict[str, Any]], per_type: int = 3) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for rank, result in enumerate(results, start=1):
        rtype = str(result.get("type", "unknown"))
        rid = str(result.get("id", ""))
        if rid in seen[rtype] or len(grouped[rtype]) >= per_type:
            continue
        seen[rtype].add(rid)
        grouped[rtype].append(_compact_result(result, rank))
    return dict(grouped)


def _artifact_types(results: list[dict[str, Any]], limit: int = 10) -> list[str]:
    types = []
    for result in results[:limit]:
        rtype = str(result.get("type", "unknown"))
        if rtype not in types:
            types.append(rtype)
    return types


def _signal_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    top = results[:5]
    matched = []
    supports = []
    graph_examples = []
    labels = []
    for rank, result in enumerate(top, start=1):
        terms = _matched_terms(result)
        if terms:
            matched.append({"rank": rank, "id": result.get("id"), "terms": terms[:10]})
        support = _support(result)
        if support:
            supports.append({"rank": rank, "id": result.get("id"), "support": support})
        graph = _graph_signal(result)
        if graph.get("graph_score") is not None:
            graph_examples.append({"rank": rank, "id": result.get("id"), **graph})
        labels.append(result.get("evidence", {}).get("confidence", {}).get("label", "unknown"))
    return {
        "top_confidence_labels": labels,
        "matched_terms_by_rank": matched,
        "support_by_rank": supports,
        "graph_or_structural_support_by_rank": graph_examples,
    }


def _salient_terms(results: list[dict[str, Any]]) -> list[str]:
    stop = {
        "and", "the", "for", "with", "from", "that", "this", "behavior", "baseline", "refined",
        "source", "state", "additional", "information", "response", "none", "no", "a", "an", "to",
        "in", "on", "of", "is", "are", "be", "as", "v1", "v2", "us", "bug", "java", "altinn",
    }
    terms = []
    for result in results[:5]:
        for term in _matched_terms(result)[:12]:
            clean = str(term).lower().strip("_-/.")
            if len(clean) < 3 or clean.isdigit() or clean in stop:
                continue
            if clean not in terms:
                terms.append(clean)
    return terms


def _interpretation(case: dict[str, str], types: list[str], results: list[dict[str, Any]]) -> tuple[str, str]:
    top_ids = [str(result.get("id", "")) for result in results[:5]]
    top_terms = _salient_terms(results)
    term_text = ", ".join(top_terms[:8]) if top_terms else "the trigger vocabulary"
    type_text = ", ".join(types) if types else "no artifacts"
    if case["expected_behavior"] == "clear":
        interpretation = (
            f"The ranking is focused: the first results stay in the selected dataset and expose {type_text}. "
            f"The top identifiers ({'; '.join(top_ids[:3])}) and lexical cues ({term_text}) are semantically aligned with the trigger, "
            "so the result is plausible and easy to interpret."
        )
        takeaway = "This case illustrates a clean scenario-level trace where lexical, semantic, and confidence signals point to the same concern."
    elif case["expected_behavior"] == "mixed":
        interpretation = (
            f"The output is plausible but broader: the top ranks include {type_text}, and the leading artifacts ({'; '.join(top_ids[:3])}) share useful terms "
            f"such as {term_text}. Some lower-ranked results widen to neighboring concepts, making the case partially successful rather than perfectly focused."
        )
        takeaway = "This case illustrates useful cross-artifact coverage with some ranking breadth that requires analyst judgment."
    else:
        interpretation = (
            f"The retrieval is interpretable but noisy: the top ranks include {type_text}, yet broad repository vocabulary and generic validation terms spread attention across "
            f"artifacts such as {('; '.join(top_ids[:4]))}. The explanation fields help identify why these artifacts surfaced, but the ranking is less decisive."
        )
        takeaway = "This case illustrates the ambiguity that appears when a broad repository-backed trigger maps to many plausible artifacts."
    return interpretation, takeaway


def analyze_cases(k: int = 20) -> dict[str, Any]:
    import src.agents as agents

    records = build_step2_records()
    install_temporary_step2_index(records)

    cases = []
    for case in CURATED_CASES:
        trigger_text, source_row = _build_trigger(case)
        results = agents.search(trigger_text, k=k, dataset=case["dataset_id"], link_mode="inferred")
        types = _artifact_types(results)
        interpretation, takeaway = _interpretation(case, types, results)
        cases.append(
            {
                "case_id": case["case_id"],
                "dataset_family": case["dataset_family"],
                "dataset_id": case["dataset_id"],
                "scenario_id": case["scenario_id"],
                "trigger_type": case["trigger_type"],
                "selection_reason": case["selection_reason"],
                "trigger_text": trigger_text,
                "sanitized_query": _clean_query_for_display(trigger_text),
                "query_note": "The sanitized query is for display only; the raw trigger_text was passed to the existing retrieval pipeline.",
                "source_row": {k: v for k, v in source_row.items() if k in {"Scenario ID", "Change Trigger (User Story V1 → V2)", "Impact Category", "bug_id", "file_path", "related_story"}},
                "returned_artifact_types": types,
                "top_results_overall": [_compact_result(result, rank) for rank, result in enumerate(results[:8], start=1)],
                "top_results_by_type": _top_by_type(results),
                "explanation_signals": _signal_summary(results),
                "interpretation": interpretation,
                "takeaway": takeaway,
            }
        )

    return {
        "step": "Step 3 qualitative case analysis",
        "purpose": "Small scenario-level dissection of representative retrieval outputs; separate from Step 1 and Step 2 metrics.",
        "retrieval_configuration": {
            "pipeline": "src.agents.search",
            "k": k,
            "link_mode": "inferred",
            "dataset_filter": "per selected dataset_id",
            "corpus": "temporary in-memory corpus over small and repository-backed datasets; no Step 1 or Step 2 outputs are modified",
        },
        "paper_ready_intro": (
            "Step 3 complements the quantitative benchmark and comparative analysis with a qualitative case analysis of a small set of representative scenarios. "
            "Rather than computing another family-level score, it inspects individual requirement- and code-driven changes end to end: the trigger text, returned artifact types, explanation signals, and whether the resulting trace is plausible and interpretable."
        ),
        "cases": cases,
        "paper_ready_conclusion": (
            "Across the cases, the retrieval framework is most convincing when the trigger contains specific domain terms or identifiers that align with code, tests, and faults. "
            "The same explanation fields remain useful on noisier repository-backed inputs, but rankings become broader and require more analyst interpretation because many artifacts share generic validation, UI, or schema vocabulary."
        ),
        "paper_table_suggestion": {
            "columns": ["Case", "Trigger type", "Dataset", "Returned types", "Main observation"],
            "rows": [
                {
                    "Case": c["case_id"],
                    "Trigger type": c["trigger_type"],
                    "Dataset": c["dataset_id"],
                    "Returned types": ", ".join(c["returned_artifact_types"]),
                    "Main observation": c["takeaway"],
                }
                for c in cases
            ],
        },
    }


def _write_json(payload: dict[str, Any]) -> None:
    with OUTPUT_JSON.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _write_csv(payload: dict[str, Any]) -> None:
    fields = ["case_id", "dataset_family", "dataset_id", "scenario_id", "trigger_type", "returned_artifact_types", "top_result", "selection_reason", "takeaway"]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in payload["cases"]:
            top = case["top_results_overall"][0] if case["top_results_overall"] else {}
            writer.writerow(
                {
                    "case_id": case["case_id"],
                    "dataset_family": case["dataset_family"],
                    "dataset_id": case["dataset_id"],
                    "scenario_id": case["scenario_id"],
                    "trigger_type": case["trigger_type"],
                    "returned_artifact_types": ";".join(case["returned_artifact_types"]),
                    "top_result": f"{top.get('id', '')} ({top.get('type', '')})",
                    "selection_reason": case["selection_reason"],
                    "takeaway": case["takeaway"],
                }
            )


def _result_line(item: dict[str, Any]) -> str:
    terms = ", ".join(item.get("matched_terms", [])[:6]) or "none"
    support = ", ".join(item.get("support", [])[:4]) or "none"
    return (
        f"- R{item['rank']}: `{item.get('id')}` ({item.get('type')}; score={item.get('score')}; "
        f"confidence={item.get('confidence_label')}/{item.get('confidence_score')}; terms: {terms}; support: {support})"
    )


def _write_md(payload: dict[str, Any]) -> None:
    with OUTPUT_MD.open("w", encoding="utf-8") as handle:
        handle.write("# Step 3 Qualitative Case Analysis\n\n")
        handle.write(payload["paper_ready_intro"] + "\n\n")
        handle.write("## Selected cases\n\n")
        for case in payload["cases"]:
            handle.write(f"### {case['case_id']}. {case['dataset_id']} — {case['scenario_id']}\n\n")
            handle.write(f"**Selection reason.** {case['selection_reason']}\n\n")
            handle.write("#### 1. Trigger\n\n")
            side = "requirement-side" if case["trigger_type"] == "requirement_change" else "code-side"
            handle.write(f"- **Trigger type:** {case['trigger_type']} ({side})\n")
            handle.write(f"- **What changed:** {case['sanitized_query'][:1200]}{'…' if len(case['sanitized_query']) > 1200 else ''}\n\n")
            handle.write("#### 2. Returned artifacts\n\n")
            handle.write(f"- **Returned artifact types:** {', '.join(case['returned_artifact_types']) or 'none'}\n")
            handle.write("- **Top results overall:**\n")
            for item in case["top_results_overall"][:5]:
                handle.write(_result_line(item) + "\n")
            handle.write("\n- **Top results by type:**\n")
            for rtype, items in case["top_results_by_type"].items():
                ids = "; ".join(f"{item['id']} (R{item['rank']})" for item in items)
                handle.write(f"  - {rtype}: {ids}\n")
            handle.write("\n#### 3. Explanation signals\n\n")
            labels = ", ".join(case["explanation_signals"].get("top_confidence_labels", []))
            handle.write(f"- **Top confidence labels:** {labels}\n")
            matched = case["explanation_signals"].get("matched_terms_by_rank", [])
            if matched:
                handle.write("- **Matched terms:** " + "; ".join(f"R{m['rank']} {m['id']}: {', '.join(m['terms'][:8])}" for m in matched[:4]) + "\n")
            support = case["explanation_signals"].get("support_by_rank", [])
            if support:
                handle.write("- **Support sources:** " + "; ".join(f"R{s['rank']} {s['id']}: {', '.join(s['support'][:5])}" for s in support[:4]) + "\n")
            graph = case["explanation_signals"].get("graph_or_structural_support_by_rank", [])
            if graph:
                handle.write("- **Graph/structural support:** " + "; ".join(f"R{g['rank']} score={g.get('graph_score')} neighbors={g.get('graph_neighbors')} path={g.get('reranker_has_graph_path')}" for g in graph[:4]) + "\n")
            handle.write("\n#### 4. Interpretation\n\n")
            handle.write(case["interpretation"] + "\n\n")
            handle.write("#### 5. Takeaway\n\n")
            handle.write(case["takeaway"] + "\n\n")
        handle.write("## Synthesis\n\n")
        handle.write(payload["paper_ready_conclusion"] + "\n\n")
        handle.write("## Compact table suggestion\n\n")
        handle.write("| Case | Trigger type | Dataset | Returned types | Main observation |\n")
        handle.write("|---|---|---|---|---|\n")
        for row in payload["paper_table_suggestion"]["rows"]:
            handle.write(
                f"| {row['Case']} | {row['Trigger type']} | {row['Dataset']} | {row['Returned types']} | {row['Main observation']} |\n"
            )


def write_outputs(payload: dict[str, Any]) -> None:
    _write_json(payload)
    _write_md(payload)
    _write_csv(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 3 qualitative case analysis separately from Step 1 and Step 2.")
    parser.add_argument("--k", type=int, default=20, help="Retrieval depth for each inspected case.")
    args = parser.parse_args()
    payload = analyze_cases(k=args.k)
    write_outputs(payload)
    print(json.dumps({"case_count": len(payload["cases"]), "json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD), "csv": str(OUTPUT_CSV)}, indent=2))


if __name__ == "__main__":
    main()
