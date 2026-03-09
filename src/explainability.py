from __future__ import annotations


def _safe(value, default=0.0):
    return default if value is None else value


def format_explanation(result: dict) -> str:
    """Create a compact human-readable explanation for one retrieved artifact."""
    evidence = result.get("evidence", {})
    factors = evidence.get("factorized_explanation", {})

    if not factors:
        fallback_reason = result.get("explanation_reason")
        return fallback_reason or "explanation unavailable (missing retrieval evidence)"

    dense = factors.get("dense_index", {})
    bm25 = factors.get("bm25_index", {})
    graph = factors.get("graph_index", {})
    confidence = evidence.get("confidence", {})

    matched_terms = bm25.get("matched_terms") or []
    matched_terms_text = ", ".join(matched_terms[:5]) if matched_terms else "none"

    final_score = _safe(evidence.get("final_score"))
    dense_score = _safe(dense.get("score"))
    bm25_score = _safe(bm25.get("score"))
    graph_score = _safe(graph.get("score"))
    confidence_score = _safe(confidence.get("score"))
    support = confidence.get("source_of_support") or []
    support_text = ", ".join(support) if support else "none"
    contradiction = bool(confidence.get("contradiction_signal", False))
    abstain = bool(confidence.get("abstain", False))
    abstain_text = "insufficient evidence" if abstain else "sufficient evidence"
    contradiction_text = "weak agreement across signals" if contradiction else "signals in agreement"

    return (
        f"score={final_score:.4f} "
        f"(dense={dense_score:.4f}, lexical={bm25_score:.4f}, graph={graph_score:.4f}) "
        f"terms=[{matched_terms_text}] "
        f"confidence={confidence_score:.4f} "
        f"support=[{support_text}] "
        f"contradiction={contradiction_text} "
        f"abstain={abstain_text}"
    )


def summarize_results(results: list[dict], max_items: int = 5) -> list[str]:
    """Build bullet-point style summaries with explanations."""
    output = []
    for result in results[:max_items]:
        rid = result.get("id", "unknown")
        rtype = result.get("type", "unknown")
        output.append(f"{rid} ({rtype}) -> {format_explanation(result)}")
    return output
