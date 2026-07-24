"""
CLI: re-ingest all files currently in storage/ into Pinecone.

  python -m ingestion
"""

from ingestion.service import ingest_all_storage_files


def main() -> None:
    results = ingest_all_storage_files()
    if not results:
        print("No supported files found in storage/.")
        return

    total = 0
    for item in results:
        print(
            f"Ingested {item['filename']}: "
            f"{item['chunks']} chunks ({item['chars']} chars)"
        )
        total += item["chunks"]

    print(f"Done. Upserted {total} chunks into Pinecone.")


if __name__ == "__main__":
    main()
