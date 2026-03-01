import json
import os

import faiss
import numpy as np

BASE = os.path.dirname(os.path.dirname(__file__))
FAISS_INDEX = os.path.join(BASE, "embeddings", "index.faiss")
EMB_FILE = os.path.join(BASE, "embeddings", "embeddings.npy")
META_FILE = os.path.join(BASE, "embeddings", "metadata.json")


def create_index(embeddings, metadata: list[dict]):
    emb = np.asarray(embeddings, dtype=np.float32)
    if emb.ndim != 2:
        raise ValueError("Embeddings must be a 2D array [num_records, dim].")
    if len(metadata) != emb.shape[0]:
        raise ValueError("Metadata and embeddings size mismatch.")

    os.makedirs(os.path.dirname(FAISS_INDEX), exist_ok=True)

    index = faiss.IndexFlatL2(emb.shape[1])
    index.add(emb)

    faiss.write_index(index, FAISS_INDEX)
    np.save(EMB_FILE, emb)
    with open(META_FILE, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    return index


def load_index():
    index = faiss.read_index(FAISS_INDEX)
    emb = np.load(EMB_FILE)
    with open(META_FILE, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    return index, emb, meta
