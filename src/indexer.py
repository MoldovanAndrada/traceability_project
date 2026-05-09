import importlib.util
import json
import math
import os
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(__file__))
EMB_DIR = os.path.join(BASE, "embeddings")
FAISS_INDEX = os.path.join(EMB_DIR, "index.faiss")
EMB_FILE = os.path.join(EMB_DIR, "embeddings.npy")
EMB_JSON_FILE = os.path.join(EMB_DIR, "embeddings.json")
META_FILE = os.path.join(EMB_DIR, "metadata.json")


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


class SimpleVectorIndex:
    """Small in-memory L2 index used when FAISS/NumPy are unavailable or binary output is disabled."""

    def __init__(self, vectors):
        self.vectors = [list(map(float, vector)) for vector in vectors]

    @staticmethod
    def _as_query_vector(queries):
        """Return the first query vector without truth-testing NumPy-like arrays."""
        if queries is None:
            return []
        if hasattr(queries, "tolist"):
            queries = queries.tolist()
        try:
            if len(queries) == 0:
                return []
        except TypeError:
            queries = [queries]
        query = queries[0]
        if hasattr(query, "tolist"):
            query = query.tolist()
        return list(map(float, query))

    def search(self, queries, k: int):
        query = self._as_query_vector(queries)
        distances = []
        for idx, vector in enumerate(self.vectors):
            distance = sum((a - b) * (a - b) for a, b in zip(query, vector))
            if len(vector) > len(query):
                distance += sum(value * value for value in vector[len(query):])
            elif len(query) > len(vector):
                distance += sum(value * value for value in query[len(vector):])
            distances.append((math.sqrt(distance), idx))
        distances.sort(key=lambda item: item[0])
        top = distances[:k]
        return [[item[0] for item in top]], [[item[1] for item in top]]


def _to_plain_vectors(embeddings):
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(map(float, vector)) for vector in embeddings]


def create_index(embeddings, metadata: list[dict], write_binary: bool = False):
    vectors = _to_plain_vectors(embeddings)
    if not vectors or not isinstance(vectors[0], list):
        raise ValueError("Embeddings must be a 2D array/list [num_records, dim].")
    if len(metadata) != len(vectors):
        raise ValueError("Metadata and embeddings size mismatch.")

    os.makedirs(EMB_DIR, exist_ok=True)
    with open(META_FILE, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
    with open(EMB_JSON_FILE, "w", encoding="utf-8") as handle:
        json.dump(vectors, handle)

    if write_binary and _has_module("faiss") and _has_module("numpy"):
        faiss = importlib.import_module("faiss")
        np = importlib.import_module("numpy")
        emb = np.asarray(vectors, dtype=np.float32)
        index = faiss.IndexFlatL2(emb.shape[1])
        index.add(emb)
        faiss.write_index(index, FAISS_INDEX)
        np.save(EMB_FILE, emb)
        return index

    return SimpleVectorIndex(vectors)


def _load_json_embeddings():
    with open(EMB_JSON_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_metadata():
    with open(META_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_index():
    meta = _load_metadata()
    if Path(EMB_JSON_FILE).exists():
        vectors = _load_json_embeddings()
        return SimpleVectorIndex(vectors), vectors, meta

    if _has_module("faiss") and _has_module("numpy") and Path(FAISS_INDEX).exists() and Path(EMB_FILE).exists():
        faiss = importlib.import_module("faiss")
        np = importlib.import_module("numpy")
        return faiss.read_index(FAISS_INDEX), np.load(EMB_FILE), meta

    from src.embedder import embed_texts

    vectors = embed_texts([record.get("text", "") for record in meta])
    return SimpleVectorIndex(vectors), vectors, meta
