
from src.embedder import model
from src.indexer import load_index

faiss_index, embeddings, metadata = load_index()

def search(query, k=10):
    q = model.encode([query])
    D, I = faiss_index.search(q, k)
    return [metadata[i] for i in I[0]]

def get_related_test_cases(story):
    return [r for r in search(story) if r["type"]=="test_case"]

def get_related_faults(story):
    return [r for r in search(story) if r["type"]=="fault"]

def get_impacted_code(story):
    return [r for r in search(story) if r["type"]=="code"]
