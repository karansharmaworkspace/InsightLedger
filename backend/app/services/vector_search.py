"""
Vector Search Service
ChromaDB-based vector storage with sentence-transformers embeddings.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

from app.services.chunking import DocumentChunker, DocumentChunk


class VectorSearchService:
    """Vector search service using ChromaDB."""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.chroma_dir = self.storage_dir / "chromadb"
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )

        self.chunker = DocumentChunker(chunk_size=512, chunk_overlap=50)
        self._embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        embeddings = self.embedder.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def index_document(self, document_id: str, text: str, metadata: Dict[str, Any] = None, tables: List[Any] = None):
        """Index a document into vector store."""
        metadata = metadata or {}

        chunks = self.chunker.chunk_document(document_id, text, tables, metadata)

        if not chunks:
            return {"indexed": 0}

        texts = [chunk.text for chunk in chunks]
        embeddings = self._get_embeddings(texts)

        ids = [chunk.chunk_id for chunk in chunks]
        metadatas = [
            {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content_type": chunk.metadata.get("content_type", "text"),
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                **{k: str(v) for k, v in metadata.items() if isinstance(v, (str, int, float, bool))},
            }
            for chunk in chunks
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        return {"indexed": len(chunks)}

    def search(self, query: str, n_results: int = 10, filters: Dict[str, Any] = None) -> List[Dict]:
        """Search for similar document chunks."""
        query_embedding = self._get_embeddings([query])[0]

        where = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is not None:
                    conditions.append({key: str(value)})
            if conditions:
                where = conditions[0] if len(conditions) == 1 else {"$and": conditions}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append({
                    "chunk_id": doc_id,
                    "document_id": results["metadatas"][0][i].get("document_id", ""),
                    "text": results["documents"][0][i],
                    "score": 1 - results["distances"][0][i],
                    "metadata": results["metadatas"][0][i],
                })

        return search_results

    def get_document_chunks(self, document_id: str) -> List[Dict]:
        """Get all chunks for a document."""
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )

        chunks = []
        if results and results["ids"]:
            for i, chunk_id in enumerate(results["ids"]):
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })

        return chunks

    def delete_document(self, document_id: str):
        """Delete all chunks for a document."""
        self.collection.delete(where={"document_id": document_id})

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": "documents",
        }
