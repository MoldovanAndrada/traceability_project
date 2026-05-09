import argparse
import json

from src.ingest import ingest_all, print_corpus_sanity, save_corpus_sanity, validate_records

__all__ = ["ingest_all"]


def rebuild_index() -> None:
    from src.embedder import embed_texts
    from src.indexer import create_index

    records = ingest_all()
    validate_records(records)
    embeddings = embed_texts([record["text"] for record in records])
    create_index(embeddings, records)
    print_corpus_sanity(records)
    save_corpus_sanity(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest and optionally rebuild the 3-dataset ground-truth retrieval corpus.")
    parser.add_argument("--sanity", action="store_true", help="Print and save sanity counts for the ingested records.")
    parser.add_argument("--rebuild-index", action="store_true", help="Regenerate embeddings/metadata.json plus text embedding artifacts needed by search (no binary files by default).")
    args = parser.parse_args()

    if args.rebuild_index:
        rebuild_index()
        return

    records = ingest_all()
    validate_records(records)
    summary = print_corpus_sanity(records) if args.sanity else save_corpus_sanity(records)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
