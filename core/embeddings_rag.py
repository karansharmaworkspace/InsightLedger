"""Embeddings-based RAG for semantic search over document corpus.

Uses sentence-transformers for embeddings and cosine similarity for retrieval.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingsRAG:
    """Semantic search using sentence embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "storage", "embeddings.json")
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self.chunks: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._loaded = False
        self._dirty = False  # ponytail: batch saves, flush() for explicit persistence

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def load(self) -> "EmbeddingsRAG":
        if self._loaded:
            return self
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.chunks = data.get("chunks", [])
                emb_list = data.get("embeddings", [])
                if emb_list:
                    self._embeddings = np.array(emb_list)
                self._loaded = True
            except Exception as e:
                print(f"[EMBED-RAG] Load error: {e}")
        return self

    def save(self):
        data = {
            "model_name": self.model_name,
            "chunks": self.chunks,
            "embeddings": self._embeddings.tolist() if self._embeddings is not None else [],
        }
        self.storage_path.write_text(json.dumps(data), encoding="utf-8")
        self._dirty = False

    def flush(self):
        """Persist to disk if there are pending changes."""
        if self._dirty:
            self.save()

    def add_chunks(self, chunks: list[dict[str, Any]]):
        """Add document chunks and compute embeddings."""
        texts = [c["content"][:512] for c in chunks]  # Truncate for model
        new_embeddings = self.model.encode(texts, show_progress_bar=False)

        if self._embeddings is None:
            self._embeddings = new_embeddings
            self.chunks = chunks
        else:
            self._embeddings = np.vstack([self._embeddings, new_embeddings])
            self.chunks.extend(chunks)

        self._loaded = True
        self._dirty = True

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        """Retrieve most relevant chunks using cosine similarity."""
        if not self.chunks or self._embeddings is None:
            return []

        query_embedding = self.model.encode([query])

        # Cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        normed = self._embeddings / (norms + 1e-8)
        query_normed = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        similarities = normed @ query_normed.T

        top_indices = np.argsort(similarities.flatten())[::-1][:top_k]
        results = []
        for idx in top_indices:
            chunk = dict(self.chunks[idx])
            chunk["score"] = float(similarities.flatten()[idx])
            results.append(chunk)
        return results

    def clear(self):
        """Clear all stored embeddings."""
        self.chunks = []
        self._embeddings = None
        self._loaded = False
        if self.storage_path.exists():
            self.storage_path.unlink()

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_chunks": len(self.chunks),
            "model": self.model_name,
            "embedding_dim": self._embeddings.shape[1] if self._embeddings is not None else 0,
        }
