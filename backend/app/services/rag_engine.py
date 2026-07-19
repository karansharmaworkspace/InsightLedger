"""
RAG Query Engine Service
Retrieval-Augmented Generation with CAG caching.
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.services.vector_search import VectorSearchService
from app.services.knowledge_graph import KnowledgeGraphService


# Groq free tier models (in order of preference)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


class RAGEngine:
    """RAG query engine with CAG caching."""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.cache_dir = self.storage_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.vector_service = VectorSearchService(storage_dir)
        self.kg_service = KnowledgeGraphService(storage_dir)

        self._groq_client = None
        self._model_index = 0

    @property
    def groq_client(self):
        if self._groq_client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                from groq import Groq
                self._groq_client = Groq(api_key=api_key)
        return self._groq_client

    @property
    def current_model(self):
        return GROQ_MODELS[self._model_index]

    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()

    def _get_cached(self, query: str) -> Optional[Dict]:
        """Get cached response if available."""
        cache_key = self._get_cache_key(query)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                if datetime.fromisoformat(data["cached_at"]).timestamp() > datetime.now().timestamp() - 86400:
                    return data
            except Exception:
                pass
        return None

    def _set_cached(self, query: str, response: Dict):
        """Cache response."""
        cache_key = self._get_cache_key(query)
        cache_file = self.cache_dir / f"{cache_key}.json"
        response["cached_at"] = datetime.now().isoformat()
        cache_file.write_text(json.dumps(response, indent=2, default=str), encoding="utf-8")

    def _build_context(self, query: str) -> str:
        """Build context from vector search and knowledge graph."""
        search_results = self.vector_service.search(query, n_results=5)

        context_parts = []
        for result in search_results:
            context_parts.append(f"[Source: {result['document_id']}]\n{result['text']}")

        kg_results = self.kg_service.search(query)
        if kg_results:
            kg_text = "\n".join([f"- {r.get('tag', r.get('name', r.get('description', '')))}" for r in kg_results[:5]])
            context_parts.append(f"[Knowledge Graph]\n{kg_text}")

        return "\n\n---\n\n".join(context_parts)

    def query(self, query: str, use_cache: bool = True) -> Dict[str, Any]:
        if use_cache:
            cached = self._get_cached(query)
            if cached:
                cached["from_cache"] = True
                return cached

        context = self._build_context(query)

        if self.groq_client:
            answer = None
            for attempt, model in enumerate(GROQ_MODELS):
                try:
                    response = self.groq_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an industrial knowledge assistant. Answer questions based on the provided context. Always cite sources."},
                            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
                        ],
                        max_tokens=1000,
                        temperature=0.3,
                    )
                    answer = response.choices[0].message.content
                    self._model_index = attempt
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < len(GROQ_MODELS) - 1:
                        continue
                    answer = f"Error generating response: {str(e)}"

            if answer is None:
                answer = self._fallback_response(query, context)
        else:
            answer = self._fallback_response(query, context)

        result = {
            "query": query,
            "answer": answer,
            "sources": [r["document_id"] for r in self.vector_service.search(query, n_results=3)],
            "from_cache": False,
            "model_used": self.current_model,
        }

        if use_cache:
            self._set_cached(query, result)

        return result

    def _fallback_response(self, query: str, context: str) -> str:
        """Generate fallback response without OpenAI."""
        if not context.strip():
            return "I couldn't find relevant information in the knowledge base for your query."

        return f"Based on the available documents:\n\n{context[:500]}..."

    def invalidate_cache(self, document_id: str):
        """Invalidate cache entries related to a document."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                if document_id in data.get("sources", []):
                    cache_file.unlink()
            except Exception:
                pass

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        return {
            "total_entries": len(cache_files),
            "cache_dir": str(self.cache_dir),
        }
