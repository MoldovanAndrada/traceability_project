import csv
import json
import re
from collections import Counter
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

from src.graph_store import GraphStore

BASE = Path(__file__).resolve().parent.parent
METADATA_PATH = BASE / "embeddings" / "metadata.json"
EMBEDDINGS_PATH = BASE / "embeddings" / "embeddings.npy"
GROUND_TRUTH_PATH = BASE / "traceability_lang" / "(FOR TESTING) ground_truth_story_modification.csv"

TOKEN_PATTERN = re.compile(r"\b\w+\b")
ID_PATTERN = re.compile(r"\b(?:US|TC|BUG)-\d+\b", re.IGNORECASE)
RANGE_PATTERN = re.compile(r"\b(TC|BUG)-(\d+)\s+to\s+(?:TC|BUG)-(\d+)\b", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall((text or "").lower())


def minmax(values: list[float]) -> list[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 1e-12:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def bm25_scores(query: str, docs: list[dict]) -> list[float]:
    doc_tokens = [tokenize(d.get("text", "")) for d in docs]
    doc_lens = [len(t) for t in doc_tokens]
    avgdl = sum(doc_lens) / max(len(doc_lens), 1)

    df = Counter()
    for toks in doc_tokens:
        df.update(set(toks))

    idf = {
        term: np.log(1.0 + (len(docs) - freq + 0.5) / (freq + 0.5))
        for term, freq in df.items()
    }

    k1 = 1.5
    b = 0.75
    q_counts = Counter(tokenize(query))
    scores = [0.0] * len(docs)
    for i, toks in enumerate(doc_tokens):
        if not toks:
            continue
        tf = Counter(toks)
        dl = len(toks)
        total = 0.0
        for term, qf in q_counts.items():
            if term not in tf:
                continue
            numer = tf[term] * (k1 + 1.0)
            denom = tf[term] + k1 * (1.0 - b + b * dl / max(avgdl, 1e-9))
            total += idf.get(term, 0.0) * (numer / max(denom, 1e-9)) * qf
        scores[i] = float(total)
    return scores


def parse_expected_ids(raw: str) -> set[str]:
    text = raw or ""
    expected = {m.group(0).upper() for m in ID_PATTERN.finditer(text)}
    for m in RANGE_PATTERN.finditer(text):
        prefix = m.group(1).upper()
        start = int(m.group(2))
        end = int(m.group(3))
        if end >= start:
            for num in range(start, end + 1):
                expected.add(f"{prefix}-{num:03d}")
    return expected


def parse_expected_code(raw: str, docs: list[dict]) -> set[str]:
    names = [part.strip() for part in (raw or "").split(",") if part.strip()]
    if not names:
        return set()

    expected = set()
    for rec in docs:
        if rec.get("type") != "code":
            continue
        rid = str(rec.get("id", "")).replace("\\", "/")
        text = str(rec.get("text", "")).lower()
        for name in names:
            if name.lower() in rid.lower() or f"class {name.lower()}" in text:
                expected.add(rid)
    return expected


def evaluate_mode(mode: str, docs: list[dict], embeddings, scenarios: list[dict], k: int = 10) -> dict:
    graph = GraphStore(docs, edges_path=str(BASE / "embeddings" / "edges.json"), embeddings=embeddings)

    total_expected = 0
    total_found = 0
    total_predicted = 0
    hit_scenarios = 0

    for scenario in scenarios:
        query = scenario["Change Trigger (User Story V1 → V2)"]
        expected = set()
        expected |= parse_expected_ids(scenario.get("Affected TCs (Ground Truth)", ""))
        expected |= parse_expected_ids(scenario.get("Relevant Faults (Ground Truth)", ""))
        expected_code = parse_expected_code(scenario.get("Impacted Code Artifacts", ""), docs)
        expected |= expected_code
        if not expected:
            continue

        bm25_raw = bm25_scores(query, docs)
        seed_indices = set(sorted(range(len(docs)), key=lambda i: bm25_raw[i], reverse=True)[:5])
        ppr_raw = graph.personalized_pagerank(seed_indices, link_mode=mode)

        bm25_norm = minmax(bm25_raw)
        ppr_norm = minmax(ppr_raw)
        merged = [0.7 * bm25_norm[i] + 0.3 * ppr_norm[i] for i in range(len(docs))]
        top = sorted(range(len(docs)), key=lambda i: merged[i], reverse=True)[:k]

        predicted_ids = set()
        for idx in top:
            rec = docs[idx]
            rid = str(rec.get("id", "")).replace("\\", "/")
            predicted_ids.add(rid.upper() if rec.get("type") != "code" else rid)

        matches = expected & predicted_ids
        total_expected += len(expected)
        total_found += len(matches)
        total_predicted += len(predicted_ids)
        if matches:
            hit_scenarios += 1

    precision = total_found / total_predicted if total_predicted else 0.0
    recall = total_found / total_expected if total_expected else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "mode": mode,
        "scenarios_with_hit": hit_scenarios,
        "precision@k": round(precision, 4),
        "recall@k": round(recall, 4),
        "f1@k": round(f1, 4),
    }


def load_scenarios() -> list[dict]:
    with GROUND_TRUTH_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    if np is None:
        raise SystemExit("numpy is required to run evaluation (install requirements.txt)")

    docs = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    embeddings = np.load(EMBEDDINGS_PATH)
    scenarios = load_scenarios()

    modes = ["explicit", "inferred", "combined"]
    results = [evaluate_mode(m, docs, embeddings, scenarios, k=10) for m in modes]

    print("Link-mode evaluation (traceability_lang ground truth)")
    for row in results:
        print(
            f"- {row['mode']:>8}: "
            f"precision@10={row['precision@k']:.4f}, "
            f"recall@10={row['recall@k']:.4f}, "
            f"f1@10={row['f1@k']:.4f}, "
            f"scenario_hits={row['scenarios_with_hit']}"
        )


if __name__ == "__main__":
    main()
