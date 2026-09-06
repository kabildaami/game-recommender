"""Build the complete RAG index: load -> chunk -> embed -> save."""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH, EMBEDDING_MODEL
from rag.chunker import GameChunker
from rag.embedder import GameEmbedder
from rag.saver import ChromaGameSaver


class GameRAGPipeline:
    def __init__(self) -> None:
        self.chunker = GameChunker(DATABASE_PATH)
        self.embedder = GameEmbedder()
        self.saver = ChromaGameSaver()

    def build(self, rebuild: bool = True) -> int:
        started = time.perf_counter()
        games = self.chunker.load_games()
        if not games:
            raise ValueError(
                f"No games found in {DATABASE_PATH}. Fill rag/game_database.json first."
            )

        chunks = self.chunker.create_chunks()
        print(f"Loaded games: {len(games)}")
        print(f"Created chunks: {len(chunks)}")
        print(f"Embedding model: {EMBEDDING_MODEL}")

        embeddings = self.embedder.embed_documents([chunk.text for chunk in chunks])
        stored = self.saver.save(chunks, embeddings, reset=rebuild)

        elapsed = time.perf_counter() - started
        print(f"Stored vectors: {stored}")
        print(f"RAG build completed in {elapsed:.2f}s")
        return stored


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the game RAG vector database")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete and recreate the Chroma collection before saving.",
    )
    args = parser.parse_args()
    GameRAGPipeline().build(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
