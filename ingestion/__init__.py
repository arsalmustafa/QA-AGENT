"""Ingestion package: upload → storage → text → Pinecone."""

from ingestion.service import upload_and_process, ingest_all_storage_files

__all__ = ["upload_and_process", "ingest_all_storage_files"]
