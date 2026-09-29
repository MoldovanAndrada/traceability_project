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

    def search(self, queries, k: int):
        query = list(map(float, queries[0])) if len(queries) else []
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


class FaissVectorIndex:
    """Normalize queries before forwarding them to FAISS.

    Sentence Transformers returns a NumPy array, while the dependency-free
    embedder returns a Python list.  FAISS only accepts contiguous float32
    arrays, so keeping this conversion at the index boundary makes both
    embedding backends interchangeable.
    """

    def __init__(self, index, numpy_module):
        self.index = index
        self.np = numpy_module

    @property
    def d(self):
        return self.index.d

    @property
    def ntotal(self):
        return self.index.ntotal

    def search(self, queries, k: int):
        query_array = self.np.ascontiguousarray(queries, dtype=self.np.float32)
        if query_array.ndim != 2:
            raise ValueError("Search queries must be a 2D array/list [num_queries, dim].")
        if query_array.shape[1] != self.d:
            raise ValueError(
                f"Search query dimension {query_array.shape[1]} does not match "
                f"the FAISS index dimension {self.d}. Re-run ingest.py to rebuild the index."
            )
        return self.index.search(query_array, k)


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
        index = faiss.read_index(FAISS_INDEX)
        vectors = np.load(EMB_FILE)
        if (
            vectors.ndim == 2
            and len(vectors) == len(meta) == index.ntotal
            and vectors.shape[1] == index.d
        ):
            return FaissVectorIndex(index, np), vectors, meta

        # A partial or stale binary index must not be paired with newer
        # metadata: its result IDs would refer to the wrong records. Rebuild a
        # safe in-memory index instead. The next ingest run can persist it.
        from src.embedder import embed_texts

        vectors = embed_texts([record.get("text", "") for record in meta])
        return SimpleVectorIndex(vectors), vectors, meta

    from src.embedder import embed_texts

    vectors = embed_texts([record.get("text", "") for record in meta])
    return SimpleVectorIndex(vectors), vectors, meta
