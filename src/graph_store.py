import json
import os
import re
from collections import defaultdict

_STORY_REF_PATTERN = re.compile(r"US-\d+", re.IGNORECASE)


class GraphStore:
    """In-memory graph store used as a baseline for graph-aware retrieval.

    Nodes are metadata records loaded from embeddings/metadata.json.
    Edges are loaded from embeddings/edges.json when present, otherwise inferred
    from shared story references in document text.
    """

    def __init__(self, docs: list[dict], edges_path: str | None = None):
        self.docs = docs
        self.id_to_index = {
            str(doc.get("id") or doc.get("artifact_id") or i): i for i, doc in enumerate(docs)
        }
        self.nodes = list(range(len(docs)))
        self.adjacency: dict[int, set[int]] = {i: set() for i in self.nodes}

        loaded = False
        if edges_path and os.path.exists(edges_path):
            loaded = self._load_edges(edges_path)

        if not loaded:
            self._infer_edges_from_refs()

    def _load_edges(self, edges_path: str) -> bool:
        try:
            with open(edges_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return False

        if not isinstance(payload, list):
            return False

        added = 0
        for edge in payload:
            if not isinstance(edge, dict):
                continue
            src = str(edge.get("src_id", ""))
            dst = str(edge.get("dst_id", ""))
            if src not in self.id_to_index or dst not in self.id_to_index:
                continue
            src_idx = self.id_to_index[src]
            dst_idx = self.id_to_index[dst]
            if src_idx == dst_idx:
                continue
            self.adjacency[src_idx].add(dst_idx)
            self.adjacency[dst_idx].add(src_idx)
            added += 1
        return added > 0

    def _infer_edges_from_refs(self) -> None:
        """Infer undirected edges from shared story IDs in text/id fields."""
        ref_to_nodes: dict[str, set[int]] = defaultdict(set)

        for i, doc in enumerate(self.docs):
            text = str(doc.get("text", ""))
            doc_type = str(doc.get("type", "")).lower()
            doc_id = str(doc.get("id", "")).upper()

            refs = {m.group(0).upper() for m in _STORY_REF_PATTERN.finditer(text)}
            if doc_type == "story" and doc_id:
                refs.add(doc_id)

            for ref in refs:
                ref_to_nodes[ref].add(i)

        for linked_nodes in ref_to_nodes.values():
            linked_nodes = list(linked_nodes)
            for i, src in enumerate(linked_nodes):
                for dst in linked_nodes[i + 1 :]:
                    self.adjacency[src].add(dst)
                    self.adjacency[dst].add(src)

    def neighbors(self, node_index: int) -> set[int]:
        return self.adjacency.get(node_index, set())

    def personalized_pagerank(
        self,
        seed_indices: set[int],
        alpha: float = 0.85,
        max_iter: int = 30,
        tol: float = 1e-6,
    ) -> list[float]:
        """Compute a PPR baseline over the current graph.

        Returns one score per node; higher means stronger structural support
        from the query's seed nodes.
        """
        n = len(self.nodes)
        if n == 0:
            return []

        valid_seeds = {idx for idx in seed_indices if 0 <= idx < n}
        if not valid_seeds:
            return [0.0] * n

        teleport = [0.0] * n
        seed_mass = 1.0 / len(valid_seeds)
        for idx in valid_seeds:
            teleport[idx] = seed_mass

        ranks = teleport.copy()

        for _ in range(max_iter):
            new_ranks = [(1.0 - alpha) * teleport[i] for i in range(n)]

            for node in range(n):
                neigh = self.adjacency.get(node, set())
                if neigh:
                    share = alpha * ranks[node] / len(neigh)
                    for dst in neigh:
                        new_ranks[dst] += share
                else:
                    # Dangling node redistributes to teleport distribution.
                    for i in valid_seeds:
                        new_ranks[i] += alpha * ranks[node] * seed_mass

            delta = sum(abs(new_ranks[i] - ranks[i]) for i in range(n))
            ranks = new_ranks
            if delta < tol:
                break

        return ranks
