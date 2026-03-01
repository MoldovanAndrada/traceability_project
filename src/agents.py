from collections import defaultdict

from src.embedder import model
from src.indexer import bm25_search, load_index

indices = load_index()
faiss_index = indices["dense"]
embeddings = indices["embeddings"]
metadata = indices["metadata"]
bm25_index = indices["bm25"]
graph_index = indices["graph"]


def _normalize(value: str) -> str:
    return value.replace("\\", "/").lower()


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


def _dense_search(query: str, k: int) -> list[tuple[int, float]]:
    # (b) Dense index pe embeddings: semantic retrieval with FAISS + SBERT embedding.
    q = model.encode([query])
    distances, ids = faiss_index.search(q, k)
    return [(int(i), float(dist)) for i, dist in zip(ids[0], distances[0]) if i >= 0]


def _graph_expand(seed_ids: list[int], max_nodes: int = 10) -> list[int]:
    visited: list[int] = []
    seen = set()
    for node in seed_ids:
        if node in seen:
            continue
        seen.add(node)
        visited.append(node)
        for neighbor in graph_index.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                visited.append(neighbor)
            if len(visited) >= max_nodes:
                return visited
        if len(visited) >= max_nodes:
            return visited
    return visited


def search_with_explanations(query: str, k: int = 10, dataset: str | None = None) -> dict:
    # Hybrid retrieval pipeline: dense + BM25 + graph expansion.
    dense_hits = _dense_search(query, max(k * 2, 10))
    bm25_hits = bm25_search(query, bm25_index, top_k=max(k * 2, 10))

    seed_nodes = [doc_id for doc_id, _ in dense_hits[:5]] + [doc_id for doc_id, _ in bm25_hits[:5]]
    graph_hits = _graph_expand(seed_nodes, max_nodes=max(k * 2, 10))

    combined_scores: defaultdict[int, float] = defaultdict(float)
    dense_map = dict(dense_hits)
    bm25_map = dict(bm25_hits)

    for doc_id, score in dense_hits:
        combined_scores[doc_id] += score * 0.55
    for doc_id, score in bm25_hits:
        combined_scores[doc_id] += score * 0.35
    for rank, doc_id in enumerate(graph_hits):
        combined_scores[doc_id] += max(0.0, 0.10 - rank * 0.005)

    ranked = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)

    results = []
    for doc_id, score in ranked:
        record = metadata[doc_id]
        if _matches_dataset(record, dataset):
            results.append({"doc_id": doc_id, "score": score, "record": record})
        if len(results) >= k:
            break

    # (d) Factorized explanations pe evidence: separate what came from lexical/dense/graph signals.
    factorized = []
    for item in results:
        doc_id = item["doc_id"]
        record = item["record"]
        factorized.append(
            {
                "id": record.get("id", f"doc-{doc_id}"),
                "type": record.get("type", "unknown"),
                "evidence": {
                    "dense": dense_map.get(doc_id, 0.0),
                    "bm25": bm25_map.get(doc_id, 0.0),
                    "graph": 1.0 if doc_id in graph_hits else 0.0,
                },
                "why": (
                    "Dense hit for semantic similarity, BM25 for lexical overlap, "
                    "and graph adjacency for neighborhood propagation."
                ),
            }
        )

    return {
        "results": [item["record"] for item in results],
        "factorized_explanations": factorized,
        "channels": {
            "dense_top_ids": [doc_id for doc_id, _ in dense_hits[:k]],
            "bm25_top_ids": [doc_id for doc_id, _ in bm25_hits[:k]],
            "graph_expanded_ids": graph_hits[:k],
        },
    }


def search(query, k=10, dataset: str | None = None):
    return search_with_explanations(query, k=k, dataset=dataset)["results"]


def get_related_test_cases(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r["type"] == "test_case"]


def get_related_faults(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r["type"] == "fault"]


def get_impacted_code(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r["type"] == "code"]
