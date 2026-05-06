from src.ingest import ingest_all

__all__ = ["ingest_all"]


def validate_records(records: list[dict[str, str]]) -> None:
    invalid = [record for record in records if not all(record.get(k) for k in ("dataset", "type", "id", "text"))]
    if invalid:
        raise ValueError(f"Found {len(invalid)} records missing dataset/type/id/text")


def corpus_sanity(records: list[dict[str, str]]) -> dict[str, object]:
    by_dataset = Counter(record.get("dataset", "<missing>") for record in records)
    by_type = Counter(record.get("type", "<missing>") for record in records)
    return {
        "total_records": len(records),
        "counts_per_dataset": {dataset: int(by_dataset.get(dataset, 0)) for dataset in SMALL_BENCHMARK_DATASETS},
        "counts_per_artifact_type": {artifact_type: int(count) for artifact_type, count in sorted(by_type.items())},
    }


def print_corpus_sanity(records: list[dict[str, str]]) -> None:
    summary = corpus_sanity(records)
    print(f"Total records: {summary['total_records']}")
    print("Counts per dataset:")
    for dataset, count in summary["counts_per_dataset"].items():
        print(f"  {dataset}: {count}")
    print("Counts per artifact type:")
    for artifact_type, count in summary["counts_per_artifact_type"].items():
        print(f"  {artifact_type}: {count}")
    print("Sample records:")
    for record in records[:5]:
        print(f"  dataset={record.get('dataset')} type={record.get('type')} id={record.get('id')}")


def rebuild_index() -> None:
    from src.embedder import embed_texts
    from src.indexer import create_index

    records = ingest_all()
    validate_records(records)
    embeddings = embed_texts([record["text"] for record in records])
    create_index(embeddings, records)
    print_corpus_sanity(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest and optionally rebuild the small benchmark retrieval corpus.")
    parser.add_argument("--sanity", action="store_true", help="Print sanity counts for the ingested records.")
    parser.add_argument("--rebuild-index", action="store_true", help="Regenerate embeddings/metadata.json, embeddings/embeddings.npy, and embeddings/index.faiss.")
    args = parser.parse_args()

    if args.rebuild_index:
        rebuild_index()
        return

    records = ingest_all()
    validate_records(records)
    if args.sanity:
        print_corpus_sanity(records)
    else:
        print(json.dumps(corpus_sanity(records), indent=2))


if __name__ == "__main__":
    main()