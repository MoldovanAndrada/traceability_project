import json
import math
import os
import re
from collections import Counter, defaultdict

import faiss
import numpy as np

BASE = os.path.dirname(os.path.dirname(__file__))
FAISS_INDEX = os.path.join(BASE, "embeddings", "index.faiss")
EMB_FILE = os.path.join(BASE, "embeddings", "embeddings.npy")
META_FILE = os.path.join(BASE, "embeddings", "metadata.json")

TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def tokenize(text: str) -> list[str]:
    return [tok for tok in TOKEN_RE.findall((text or "").lower()) if tok not in STOPWORDS]


def load_index():
    dense_index = faiss.read_index(FAISS_INDEX)
    emb = np.load(EMB_FILE)
    meta = json.load(open(META_FILE))

    # (a) BM25 index pe text: classic lexical index over metadata text/id fields.
    bm25_index = build_bm25_index(meta)

    # (c) Graph index pe adjacency: lightweight token-overlap neighborhood graph.
    graph_index = build_graph_index(meta)

    return {
        "dense": dense_index,
        "embeddings": emb,
        "metadata": meta,
        "bm25": bm25_index,
        "graph": graph_index,
    }


def build_bm25_index(records: list[dict], k1: float = 1.5, b: float = 0.75) -> dict:
    doc_terms: dict[int, Counter] = {}
    doc_lens: dict[int, int] = {}
    doc_freq: defaultdict[str, int] = defaultdict(int)

    for i, record in enumerate(records):
        text = " ".join(
            str(record.get(field, "")) for field in ("id", "text", "path", "source", "dataset")
        )
        counts = Counter(tokenize(text))
        doc_terms[i] = counts
        doc_lens[i] = sum(counts.values())
        for token in counts:
            doc_freq[token] += 1

    avgdl = (sum(doc_lens.values()) / len(doc_lens)) if doc_lens else 0.0
    return {
        "doc_terms": doc_terms,
        "doc_lens": doc_lens,
        "doc_freq": dict(doc_freq),
        "num_docs": len(records),
        "avgdl": avgdl,
        "k1": k1,
        "b": b,
    }


def bm25_search(query: str, bm25_index: dict, top_k: int = 10) -> list[tuple[int, float]]:
    terms = tokenize(query)
    if not terms:
        return []

    num_docs = bm25_index["num_docs"]
    avgdl = bm25_index["avgdl"] or 1.0
    k1 = bm25_index["k1"]
    b = bm25_index["b"]
    doc_terms = bm25_index["doc_terms"]
    doc_lens = bm25_index["doc_lens"]
    doc_freq = bm25_index["doc_freq"]

    scores: defaultdict[int, float] = defaultdict(float)
    for term in terms:
        df = doc_freq.get(term, 0)
        if df == 0:
            continue
        idf = math.log(1 + (num_docs - df + 0.5) / (df + 0.5))
        for doc_id, counts in doc_terms.items():
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            dl = doc_lens.get(doc_id, 0)
            denom = tf + k1 * (1 - b + b * dl / avgdl)
            scores[doc_id] += idf * ((tf * (k1 + 1)) / denom)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def build_graph_index(records: list[dict], max_neighbors: int = 6) -> dict[int, list[int]]:
    token_to_docs: defaultdict[str, set[int]] = defaultdict(set)
    doc_tokens: dict[int, set[str]] = {}

    for i, record in enumerate(records):
        text = " ".join(str(record.get(field, "")) for field in ("id", "text", "path", "source"))
        tokens = set(tokenize(text))
        doc_tokens[i] = tokens
        for token in tokens:
            token_to_docs[token].add(i)

    adjacency: dict[int, list[int]] = {}
    for doc_id, tokens in doc_tokens.items():
        neighbor_scores: defaultdict[int, int] = defaultdict(int)
        for token in tokens:
            for other in token_to_docs[token]:
                if other != doc_id:
                    neighbor_scores[other] += 1
        ranked_neighbors = [
            node for node, _ in sorted(neighbor_scores.items(), key=lambda item: item[1], reverse=True)[:max_neighbors]
        ]
        adjacency[doc_id] = ranked_neighbors

    return adjacency
