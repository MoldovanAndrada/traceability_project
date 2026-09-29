import hashlib
import importlib.util
import math
import os


# Sentence Transformers uses PyTorch, but its Transformers dependency probes every
# installed backend by default.  Explicitly disable the unused TensorFlow backend
# before importing Sentence Transformers so an unrelated TensorFlow/Keras install
# cannot break application startup (or emit TensorFlow initialization warnings).
os.environ["USE_TF"] = "0"


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


class _FallbackEmbedder:
    """Lightweight deterministic embedder for dependency-constrained local runs."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, texts: list[str]):
        vectors = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in (text or "").lower().split():
                digest = hashlib.sha256(tok.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dim
                vec[idx] += 1.0
            norm = math.sqrt(sum(value * value for value in vec))
            if norm > 0:
                vec = [value / norm for value in vec]
            vectors.append(vec)
        return vectors


if _has_module("sentence_transformers"):
    SentenceTransformer = importlib.import_module("sentence_transformers").SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
else:
    model = _FallbackEmbedder()


def embed_texts(texts: list[str]):
    """Encode texts into dense vectors compatible with the project search index."""
    return model.encode(texts)
