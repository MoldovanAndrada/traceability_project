
import os, json, numpy as np, faiss

BASE = os.path.dirname(os.path.dirname(__file__))
FAISS_INDEX = os.path.join(BASE, "embeddings", "index.faiss")
EMB_FILE = os.path.join(BASE, "embeddings", "embeddings.npy")
META_FILE = os.path.join(BASE, "embeddings", "metadata.json")

def load_index():
    index = faiss.read_index(FAISS_INDEX)
    emb = np.load(EMB_FILE)
    meta = json.load(open(META_FILE))
    return index, emb, meta
