"""Persist game chunks and their embeddings in ChromaDB."""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import chromadb

from config import CHROMA_PATH, COLLECTION_NAME
from rag.chunker import GameChunk


class ChromaGameSaver:
    def __init__(
        self,
        persist_dir: Path | str = CHROMA_PATH,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))

    def _collection(self, reset: bool):
        if reset:
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def save(
        self,
        chunks: Sequence[GameChunk],
        embeddings: Sequence[Sequence[float]],
        batch_size: int = 100,
        reset: bool = True,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            raise ValueError("No chunks to save")

        collection = self._collection(reset=reset)

        for start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[start : start + batch_size]
            batch_vectors = embeddings[start : start + batch_size]
            collection.upsert(
                ids=[c.chunk_id for c in batch_chunks],
                documents=[c.text for c in batch_chunks],
                metadatas=[c.metadata for c in batch_chunks],
                embeddings=[list(v) for v in batch_vectors],
            )

        return collection.count()
