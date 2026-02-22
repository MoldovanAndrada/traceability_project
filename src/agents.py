try:
    from src.embedder import model
    from src.indexer import load_index

    faiss_index, embeddings, metadata = load_index()
    _HAS_VECTOR_STACK = True
except Exception:
    model = None
    faiss_index = None
    embeddings = None
    metadata = []
    _HAS_VECTOR_STACK = False


def _normalize(value: str) -> str:
    return value.replace("\\", "/").lower()


def _matches_dataset(record: dict, dataset: str | None) -> bool:
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


def _tokenize(text: str) -> set[str]:
    return {t for t in _normalize(text).replace("_", " ").split() if t}


def search(query, k=10, dataset: str | None = None):
    if _HAS_VECTOR_STACK:
        q = model.encode([query])
        _, I = faiss_index.search(q, k)
        return [record for i in I[0] if (record := metadata[i]) and _matches_dataset(record, dataset)]

    # Lexical fallback when embedding dependencies are unavailable.
    q_tokens = _tokenize(query)
    filtered = [r for r in metadata if _matches_dataset(r, dataset)]
    scored = []
    for r in filtered:
        text = f"{r.get('id', '')} {r.get('text', '')}"
        score = len(q_tokens & _tokenize(text))
        if score > 0:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:k]]


def get_related_test_cases(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r.get("type") == "test_case"]


def get_related_faults(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r.get("type") == "fault"]


def get_impacted_code(story, dataset: str | None = None):
    return [r for r in search(story, dataset=dataset) if r.get("type") == "code"]
