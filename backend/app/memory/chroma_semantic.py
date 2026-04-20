"""ChromaDB adapter for semantic concept embeddings (optional)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


def upsert_student_concept(student_id: str, concept_id: str, document: str, metadata: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        import chromadb

        host = settings.chromadb_host
        port = settings.chromadb_port
        token = settings.chromadb_token
        headers = {"Authorization": f"Bearer {token}"} if token else None
        client = chromadb.HttpClient(host=host, port=port, headers=headers)
        coll = client.get_or_create_collection(f"masterai_{student_id}")
        coll.upsert(
            ids=[concept_id],
            documents=[document],
            metadatas=[metadata],
        )
    except Exception as e:
        logger.debug("Chroma upsert skipped: %s", e)


def query_similar(student_id: str, query_text: str, n: int = 5) -> list[str]:
    settings = get_settings()
    try:
        import chromadb

        host = settings.chromadb_host
        port = settings.chromadb_port
        token = settings.chromadb_token
        headers = {"Authorization": f"Bearer {token}"} if token else None
        client = chromadb.HttpClient(host=host, port=port, headers=headers)
        coll = client.get_or_create_collection(f"masterai_{student_id}")
        res = coll.query(query_texts=[query_text], n_results=n)
        return res.get("documents", [[]])[0]
    except Exception as e:
        logger.debug("Chroma query skipped: %s", e)
        return []
