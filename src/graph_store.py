import json
import os
import re
from collections import defaultdict

try:
    import numpy as np
except ImportError:  # optional dependency
    np = None

_STORY_REF_PATTERN = re.compile(r"US-\d+", re.IGNORECASE)
_TEST_REF_PATTERN = re.compile(r"TC-\d+", re.IGNORECASE)
_ISSUE_REF_PATTERN = re.compile(r"(?:BUG|ISSUE)-\d+", re.IGNORECASE)
_FILE_REF_PATTERN = re.compile(r"[\w./\\-]+\.(?:java|py|js|ts|cpp|c|cs)", re.IGNORECASE)
_COMMIT_REF_PATTERN = re.compile(r"\b(?:commit|sha)[:\s]+([a-f0-9]{7,40})\b", re.IGNORECASE)


class GraphStore:
    """In-memory graph store used as a baseline for graph-aware retrieval.

    Nodes are metadata records loaded from embeddings/metadata.json.
    Edges are loaded from embeddings/edges.json when present, otherwise inferred
    from shared story references in document text.
    """

    def __init__(
        self,
        docs: list[dict],
        edges_path: str | None = None,
        embeddings: object | None = None,
        inferred_top_k: int = 3,
        inferred_min_similarity: float = 0.35,
    ):
        self.docs = docs
        self.id_to_index = {
            str(doc.get("id") or doc.get("artifact_id") or i): i for i, doc in enumerate(docs)
        }
        self.nodes = list(range(len(docs)))
        self.explicit_adjacency: dict[int, set[int]] = {i: set() for i in self.nodes}
        self.inferred_adjacency: dict[int, set[int]] = {i: set() for i in self.nodes}
        self.combined_adjacency: dict[int, set[int]] = {i: set() for i in self.nodes}

        loaded = False
        if edges_path and os.path.exists(edges_path):
            loaded = self._load_edges(edges_path)

        self._build_explicit_edges_from_refs()
        self._infer_edges_from_similarity(
            embeddings,
            top_k=max(1, int(inferred_top_k)),
            min_similarity=float(inferred_min_similarity),
        )
        self._refresh_combined_adjacency()

        # Keep a fallback explicit graph even when no references were extracted.
        if not loaded and not any(self.explicit_adjacency.values()):
            self._fallback_infer_edges_from_story_refs()
            self._refresh_combined_adjacency()

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
            self.explicit_adjacency[src_idx].add(dst_idx)
            self.explicit_adjacency[dst_idx].add(src_idx)
            added += 1
        return added > 0

    def _extract_explicit_refs(self, doc: dict) -> set[str]:
        text = str(doc.get("text", ""))
        doc_id = str(doc.get("id", ""))
        path = str(doc.get("path", ""))

        refs: set[str] = set()
        refs.update(m.group(0).upper() for m in _STORY_REF_PATTERN.finditer(text))
        refs.update(m.group(0).upper() for m in _TEST_REF_PATTERN.finditer(text))
        refs.update(m.group(0).upper() for m in _ISSUE_REF_PATTERN.finditer(text))
        refs.update(m.group(0).upper() for m in _STORY_REF_PATTERN.finditer(doc_id))
        refs.update(m.group(0).upper() for m in _TEST_REF_PATTERN.finditer(doc_id))
        refs.update(m.group(0).upper() for m in _ISSUE_REF_PATTERN.finditer(doc_id))

        refs.update(
            "PATH:" + m.group(0).replace('\\', '/').lower()
            for m in _FILE_REF_PATTERN.finditer(text)
        )
        if path:
            refs.add("PATH:" + path.replace('\\', '/').lower())

        for m in _COMMIT_REF_PATTERN.finditer(text):
            refs.add(f"COMMIT:{m.group(1).lower()}")

        # Code artifacts without extension are often cited by class name in stories.
        if doc_id:
            refs.add(f"ART:{doc_id.split('/')[-1].split('.')[-2] if '.' in doc_id else doc_id}".lower())
        return {ref for ref in refs if ref and ref != "art:"}

    def _build_explicit_edges_from_refs(self) -> None:
        """Build explicit edges from shared story/test/issue IDs and file/path mentions."""
        ref_to_nodes: dict[str, set[int]] = defaultdict(set)

        for i, doc in enumerate(self.docs):
            for ref in self._extract_explicit_refs(doc):
                ref_to_nodes[ref].add(i)

        for linked_nodes in ref_to_nodes.values():
            linked_nodes = list(linked_nodes)
            for i, src in enumerate(linked_nodes):
                for dst in linked_nodes[i + 1 :]:
                    self.explicit_adjacency[src].add(dst)
                    self.explicit_adjacency[dst].add(src)

    def _fallback_infer_edges_from_story_refs(self) -> None:
        """Fallback explicit graph when richer explicit references are absent."""
        ref_to_nodes: dict[str, set[int]] = defaultdict(set)
        for i, doc in enumerate(self.docs):
            text = str(doc.get("text", ""))
            refs = {m.group(0).upper() for m in _STORY_REF_PATTERN.finditer(text)}
            for ref in refs:
                ref_to_nodes[ref].add(i)
        for linked_nodes in ref_to_nodes.values():
            linked_nodes = list(linked_nodes)
            for i, src in enumerate(linked_nodes):
                for dst in linked_nodes[i + 1 :]:
                    self.explicit_adjacency[src].add(dst)
                    self.explicit_adjacency[dst].add(src)

    def _infer_edges_from_similarity(
        self,
        embeddings: object | None,
        top_k: int,
        min_similarity: float,
    ) -> None:
        """Build inferred edges from semantic retrieval similarity."""
        if embeddings is None or np is None:
            return
        if len(embeddings) != len(self.docs) or len(self.docs) < 2:
            return

        matrix = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normalized = matrix / norms
        sims = normalized @ normalized.T

        for i in range(len(self.docs)):
            neighbor_indices = np.argsort(-sims[i])
            selected = 0
            for j in neighbor_indices:
                if i == j:
                    continue
                similarity = float(sims[i, j])
                if similarity < min_similarity:
                    break
                self.inferred_adjacency[i].add(int(j))
                self.inferred_adjacency[int(j)].add(i)
                selected += 1
                if selected >= top_k:
                    break

    def _refresh_combined_adjacency(self) -> None:
        for idx in self.nodes:
            self.combined_adjacency[idx] = set(self.explicit_adjacency[idx]) | set(
                self.inferred_adjacency[idx]
            )

    def _adjacency_for(self, link_mode: str = "combined") -> dict[int, set[int]]:
        mode = (link_mode or "combined").lower()
        if mode == "explicit":
            return self.explicit_adjacency
        if mode == "inferred":
            return self.inferred_adjacency
        return self.combined_adjacency

    def neighbors(self, node_index: int, link_mode: str = "combined") -> set[int]:
        return self._adjacency_for(link_mode).get(node_index, set())

    def personalized_pagerank(
        self,
        seed_indices: set[int],
        alpha: float = 0.85,
        max_iter: int = 30,
        tol: float = 1e-6,
        link_mode: str = "combined",
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

        adjacency = self._adjacency_for(link_mode)

        teleport = [0.0] * n
        seed_mass = 1.0 / len(valid_seeds)
        for idx in valid_seeds:
            teleport[idx] = seed_mass

        ranks = teleport.copy()

        for _ in range(max_iter):
            new_ranks = [(1.0 - alpha) * teleport[i] for i in range(n)]

            for node in range(n):
                neigh = adjacency.get(node, set())
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
