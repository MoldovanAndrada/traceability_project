from src.embedder import model
from src.indexer import load_index

faiss_index, embeddings, metadata = load_index()


def _normalize(value: str) -> str:
    return value.replace("\\", "/").lower()


def _matches_dataset(record: dict, dataset: str | None) -> bool:
    """Best-effort filter that keeps only records belonging to one dataset."""
    if not dataset:
        return True

    dataset = _normalize(dataset)
    explicit_dataset = record.get("dataset")
    if explicit_dataset and _normalize(str(explicit_dataset)) == dataset:
        return True

    for field in ("id", "text", "path", "source"):
        value = record.get(field)
        if value and dataset in _normalize(str(value)):
            return True

    return False


def search(query, k=10, dataset: str | None = None):
    q = model.encode([query])
    D, I = faiss_index.search(q, k)
    return [record for i in I[0] if (record := metadata[i]) and _matches_dataset(record, dataset)]


def get_related_test_cases(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r["type"] == "test_case"]


def get_related_faults(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r["type"] == "fault"]


def get_impacted_code(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r["type"] == "code"]
