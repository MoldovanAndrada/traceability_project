import hashlib
import numpy as np

try:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
except ModuleNotFoundError:
    class _FallbackEmbedder:
        """Lightweight fallback so local runs work even without sentence-transformers."""

        def __init__(self, dim: int = 384):
            self.dim = dim

        def encode(self, texts: list[str]):
            vectors = []
            for text in texts:
                vec = np.zeros(self.dim, dtype=np.float32)
                for tok in (text or "").lower().split():
                    digest = hashlib.sha256(tok.encode("utf-8")).digest()
                    idx = int.from_bytes(digest[:4], "little") % self.dim
                    vec[idx] += 1.0
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                vectors.append(vec)
            return np.asarray(vectors, dtype=np.float32)

    model = _FallbackEmbedder()
