import math
import os
import re
from collections import Counter

from src.embedder import model
from src.explainability import format_explanation
from src.graph_store import GraphStore
from src.indexer import load_index

faiss_index, embeddings, metadata = load_index()

_TOKEN_PATTERN = re.compile(r"\b\w+\b")
_STORY_PATTERN = re.compile(r"US-\d+", re.IGNORECASE)
_FILE_PATTERN = re.compile(r"[\w./\\-]+\.(?:java|py|js|ts|cpp|c|cs)", re.IGNORECASE)
_BASE = os.path.dirname(os.path.dirname(__file__))
_EDGES_FILE = os.path.join(_BASE, "embeddings", "edges.json")


def _tokenize(text: str) -> list[str]:
    """Small tokenizer used by BM25 and graph linking."""
    return _TOKEN_PATTERN.findall((text or "").lower())


def _normalize(value: str) -> str:
    return value.replace("\\", "/").lower()


def _clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _extract_story_refs(*texts: str) -> set[str]:
    refs = set()
    for text in texts:
        refs.update(m.group(0).upper() for m in _STORY_PATTERN.finditer(text or ""))
    return refs


def _extract_file_refs(*texts: str) -> set[str]:
    refs = set()
    for text in texts:
        refs.update(_normalize(m.group(0)) for m in _FILE_PATTERN.finditer(text or ""))
    return refs


def _matches_dataset(record: dict, dataset: str | None) -> bool:
    """Best-effort filter that keeps only records belonging to one dataset."""
    if not dataset:
        return True

    dataset = _normalize(dataset)
    explicit_dataset = record.get("dataset")
    if explicit_dataset and _normalize(str(explicit_dataset)) == dataset:
        return True

    for field in ("id", "text", "path", "source"):
        value = record.get(field)
        if value and dataset in _normalize(str(value)):
            return True

    return False


class _HybridIndex:
    """Hybrid retrieval layer:
    (a) BM25 over raw text, (b) dense FAISS, (c) graph store with PPR propagation.
    """

    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.doc_tokens = [_tokenize(d.get("text", "")) for d in docs]
        self.doc_lens = [len(toks) for toks in self.doc_tokens]
        self.avgdl = (sum(self.doc_lens) / len(self.doc_lens)) if self.doc_lens else 0.0
        self.N = len(docs)
        self.k1 = 1.5
        self.b = 0.75

        df = Counter()
        for toks in self.doc_tokens:
            df.update(set(toks))
        self.idf = {
            term: math.log(1.0 + (self.N - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

        self.graph_store = GraphStore(docs, edges_path=_EDGES_FILE, embeddings=embeddings)

    def bm25_scores(self, query: str) -> list[float]:
        q_tokens = _tokenize(query)
        q_counts = Counter(q_tokens)
        scores = [0.0] * self.N

        for i, toks in enumerate(self.doc_tokens):
            if not toks:
                continue
            tf = Counter(toks)
            dl = self.doc_lens[i]
            score = 0.0
            for term, qf in q_counts.items():
                if term not in tf:
                    continue
                idf = self.idf.get(term, 0.0)
                freq = tf[term]
                numer = freq * (self.k1 + 1.0)
                denom = freq + self.k1 * (1.0 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                score += idf * (numer / max(denom, 1e-9)) * qf
            scores[i] = score
        return scores


class _Reranker:
    """Lightweight learned-to-rank style reranker using engineered features."""

    TYPE_PRIOR = {
        "code": 1.0,
        "test_case": 0.75,
        "fault": 0.65,
        "story": 0.55,
    }

    def __init__(self, docs: list[dict], graph_store: GraphStore):
        self.docs = docs
        self.graph_store = graph_store
        self.fault_indices = [i for i, rec in enumerate(docs) if rec.get("type") == "fault"]
        self.fault_order = {
            idx: pos / max(len(self.fault_indices) - 1, 1)
            for pos, idx in enumerate(sorted(self.fault_indices, key=lambda i: self._fault_num(docs[i])))
        }
        self.story_fault_count = Counter()
        for idx in self.fault_indices:
            refs = _extract_story_refs(docs[idx].get("id", ""), docs[idx].get("text", ""))
            self.story_fault_count.update(refs)

    def _fault_num(self, rec: dict) -> int:
        match = re.search(r"\d+", str(rec.get("id", "")))
        return int(match.group(0)) if match else 0

    def _graph_distance_score(
        self,
        i: int,
        seed_indices: set[int],
        link_mode: str = "combined",
    ) -> tuple[float, int | None, bool]:
        if not seed_indices:
            return 0.0, None, False
        if i in seed_indices:
            return 1.0, 0, True

        visited = set(seed_indices)
        frontier = list(seed_indices)
        depth = 0
        while frontier and depth < 4:
            depth += 1
            nxt = []
            for node in frontier:
                neigh = self.graph_store.neighbors(node, link_mode=link_mode)
                if i in neigh:
                    return 1.0 / (1.0 + depth), depth, True
                for n in neigh:
                    if n not in visited:
                        visited.add(n)
                        nxt.append(n)
            frontier = nxt
        return 0.0, None, False

    def _changed_line_overlap(self, query: str, rec: dict) -> float:
        changed_lines = [
            line[1:].strip()
            for line in (query or "").splitlines()
            if line.startswith(("+", "-")) and len(line.strip()) > 1
        ]
        if not changed_lines:
            return 0.0
        changed_tokens = set(_tokenize(" ".join(changed_lines)))
        if not changed_tokens:
            return 0.0

        rec_tokens = set(_tokenize(rec.get("text", "")))
        direct_overlap = len(changed_tokens & rec_tokens) / len(changed_tokens)

        # If any changed-file reference appears in known fault artifacts, boost overlap.
        query_files = _extract_file_refs(query)
        if query_files:
            basename_hits = 0
            for file_ref in query_files:
                base = file_ref.rsplit("/", 1)[-1]
                if any(base in _normalize(self.docs[f_idx].get("text", "")) for f_idx in self.fault_indices):
                    basename_hits += 1
            history_overlap = basename_hits / len(query_files)
            return _clip(0.7 * direct_overlap + 0.3 * history_overlap)
        return _clip(direct_overlap)

    def score(
        self,
        query: str,
        rec: dict,
        i: int,
        seed_indices: set[int],
        merged_score: float,
        link_mode: str = "combined",
    ) -> tuple[float, dict]:
        query_tokens = set(_tokenize(query))
        rec_tokens = set(_tokenize(rec.get("text", "")))
        lexical_overlap = len(query_tokens & rec_tokens) / max(len(query_tokens), 1)

        type_prior = self.TYPE_PRIOR.get(str(rec.get("type", "")).lower(), 0.5)

        graph_distance_score, distance, edge_exists = self._graph_distance_score(
            i, seed_indices, link_mode=link_mode
        )

        query_stories = _extract_story_refs(query)
        rec_stories = _extract_story_refs(rec.get("id", ""), rec.get("text", ""))
        same_story = 1.0 if query_stories & rec_stories else 0.0

        query_files = _extract_file_refs(query)
        rec_files = _extract_file_refs(rec.get("id", ""), rec.get("text", ""))
        same_file = 1.0 if query_files & rec_files else 0.0

        query_modules = {f.split("/")[-2] for f in query_files if "/" in f}
        rec_modules = {f.split("/")[-2] for f in rec_files if "/" in f}
        same_module = 1.0 if query_modules and (query_modules & rec_modules) else 0.0

        if rec.get("type") == "fault":
            recency = self.fault_order.get(i, 0.0)
            frequency = sum(self.story_fault_count[s] for s in rec_stories)
            frequency_score = _clip(frequency / 5.0)
        else:
            recency = 0.0
            frequency_score = 0.0

        changed_overlap = self._changed_line_overlap(query, rec)

        rerank_score = (
            0.45 * merged_score
            + 0.20 * lexical_overlap
            + 0.10 * type_prior
            + 0.10 * graph_distance_score
            + 0.05 * same_story
            + 0.03 * same_file
            + 0.02 * same_module
            + 0.03 * recency
            + 0.01 * frequency_score
            + 0.01 * changed_overlap
        )

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


HYBRID_INDEX = _HybridIndex(metadata)
RERANKER = _Reranker(metadata, HYBRID_INDEX.graph_store)


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _build_confidence_layer(
    dense_score: float,
    lexical_score: float,
    graph_score: float,
    final_score: float,
    reranker: dict,
) -> dict:
    historical = _clamp01(max(reranker.get("fault_frequency", 0.0), reranker.get("changed_lines_overlap", 0.0)))
    signals = {
        "semantic": _clamp01(dense_score),
        "lexical": _clamp01(lexical_score),
        "graph": _clamp01(graph_score),
        "historical_fault_co_location": historical,
    }

    ranked = sorted(signals.items(), key=lambda kv: kv[1], reverse=True)
    top_score = ranked[0][1]
    support_floor = max(0.35, top_score - 0.15)
    support = [name for name, score in ranked if score >= support_floor][:3]
    if not support:
        support = [ranked[0][0]]

    vals = list(signals.values())
    spread = max(vals) - min(vals)
    agreement = 1.0 - spread
    strong_count = sum(1 for v in vals if v >= 0.4)
    weak_count = sum(1 for v in vals if v < 0.25)
    # Flag contradiction only for clear disagreement. A single weak auxiliary
    # signal (for example sparse historical fault data) should not mark an
    # otherwise consistent result as contradictory.
    very_strong_count = sum(1 for v in vals if v >= 0.6)
    very_weak_count = sum(1 for v in vals if v <= 0.15)
    contradiction = (
        spread > 0.55
        or (strong_count <= 1 and top_score >= 0.6 and weak_count >= 2)
        or (very_strong_count >= 2 and very_weak_count >= 2)
    )

    top2_mean = (ranked[0][1] + ranked[1][1]) / 2.0
    confidence = _clamp01(0.55 * _clamp01(final_score) + 0.25 * top2_mean + 0.20 * agreement)

    abstain = confidence < 0.5 and (top_score < 0.55 or len(support) <= 1)
    reason = "insufficient evidence" if abstain else ""

    if confidence >= 0.75:
        label = "high"
    elif confidence >= 0.5:
        label = "medium"
    elif confidence >= 0.35:
        label = "low"
    else:
        label = "very_low"

    return {
        "score": round(confidence, 4),
        "label": label,
        "source_of_support": support,
        "contradiction_signal": contradiction,
        "signal_agreement": round(_clamp01(agreement), 4),
        "abstain": abstain,
        "reason": reason,
        "signal_scores": {k: round(v, 4) for k, v in signals.items()},
    }


def _build_factorized_explanations(
    query: str,
    dense_raw: list[float],
    bm25_raw: list[float],
    graph_raw: list[float],
    merged: list[float],
    top_indices: list[int],
    rerank_features: dict[int, dict] | None = None,
    link_mode: str = "combined",
) -> list[dict]:
    dense_norm = _minmax(dense_raw)
    bm25_norm = _minmax(bm25_raw)
    graph_norm = _minmax(graph_raw)

    explained = []
    for i in top_indices:
        record = dict(metadata[i])
        text = record.get("text", "")
        query_terms = set(_tokenize(query))
        overlap = sorted(query_terms.intersection(_tokenize(text)))[:10]

        record["evidence"] = {
            "factorized_explanation": {
                "dense_index": {
                    "score": round(float(dense_norm[i]), 4),
                    "note": "semantic similarity from embedding space",
                },
                "bm25_index": {
                    "score": round(float(bm25_norm[i]), 4),
                    "matched_terms": overlap,
                    "note": "lexical relevance from BM25 over document text",
                },
                "graph_index": {
                    "score": round(float(graph_norm[i]), 4),
                    "neighbors": len(HYBRID_INDEX.graph_store.neighbors(i, link_mode=link_mode)),
                    "method": f"personalized_pagerank[{link_mode}]",
                    "note": "structural support from graph store propagation",
                },
                "reranker": (rerank_features or {}).get(i, {}),
            },
            "final_score": round(float(merged[i]), 4),
        }

        confidence = _build_confidence_layer(
            dense_score=dense_norm[i],
            lexical_score=bm25_norm[i],
            graph_score=graph_norm[i],
            final_score=merged[i],
            reranker=(rerank_features or {}).get(i, {}),
        )
        record["evidence"]["confidence"] = confidence
        record["confidence_score"] = confidence["score"]
        record["abstain"] = confidence["abstain"]

        # Keep a first-class explanation field for callers that return raw
        # search results without post-processing (e.g., API/plugin clients).
        record["explanation"] = format_explanation(record)
        explained.append(record)
    return explained


def search(query, k=10, dataset: str | None = None, link_mode: str = "combined"):
    link_mode = (link_mode or "combined").lower()
    q = model.encode([query])
    dense_distances, dense_indices = faiss_index.search(q, min(len(metadata), max(k * 3, k)))

    dense_raw = [0.0] * len(metadata)
    for dist, i in zip(dense_distances[0], dense_indices[0]):
        if i < 0:
            continue
        dense_raw[i] = 1.0 / (1.0 + float(dist))

    bm25_raw = HYBRID_INDEX.bm25_scores(query)

    seed_indices = set()
    dense_top = sorted(range(len(dense_raw)), key=lambda idx: dense_raw[idx], reverse=True)[: max(3, k // 2)]
    bm25_top = sorted(range(len(bm25_raw)), key=lambda idx: bm25_raw[idx], reverse=True)[: max(3, k // 2)]
    seed_indices.update(dense_top)
    seed_indices.update(bm25_top)

    graph_raw = HYBRID_INDEX.graph_store.personalized_pagerank(seed_indices, link_mode=link_mode)

    dense_norm = _minmax(dense_raw)
    bm25_norm = _minmax(bm25_raw)
    graph_norm = _minmax(graph_raw)

    merged = [
        0.5 * dense_norm[i] + 0.3 * bm25_norm[i] + 0.2 * graph_norm[i]
        for i in range(len(metadata))
    ]

    rerank_scores = {}
    rerank_features = {}
    for i in range(len(metadata)):
        score, features = RERANKER.score(query, metadata[i], i, seed_indices, merged[i], link_mode=link_mode)
        rerank_scores[i] = score
        rerank_features[i] = features

    ranked_indices = sorted(range(len(metadata)), key=lambda idx: rerank_scores[idx], reverse=True)
    filtered = [i for i in ranked_indices if _matches_dataset(metadata[i], dataset)][:k]

    return _build_factorized_explanations(
        query,
        dense_raw,
        bm25_raw,
        graph_raw,
        [rerank_scores[i] for i in range(len(metadata))],
        filtered,
        rerank_features=rerank_features,
        link_mode=link_mode,
    )


def get_related_test_cases(story, dataset: str | None = None, link_mode: str = "combined"):
    return [r for r in search(story, dataset=dataset, link_mode=link_mode) if r["type"] == "test_case"]


def get_related_faults(story, dataset: str | None = None, link_mode: str = "combined"):
    return [r for r in search(story, dataset=dataset, link_mode=link_mode) if r["type"] == "fault"]


def get_impacted_code(story, dataset: str | None = None, link_mode: str = "combined"):
    return [r for r in search(story, dataset=dataset, link_mode=link_mode) if r["type"] == "code"]
