"""RAG engine over an OKF (Open Knowledge Format) bundle.

OKF is Google's open standard for representing knowledge as markdown files
with YAML frontmatter. See: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and body from markdown."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    body = parts[2].strip()
    return meta, body


def _keywords(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9_\s]", " ", text.lower())
    stops = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "and", "but", "or",
        "not", "so", "this", "that", "these", "those", "none",
    }
    return {w for w in text.split() if len(w) > 2 and w not in stops}


class OntologyRAG:
    """Reads an OKF bundle and retrieves relevant concepts."""

    def __init__(self, okf_path: str | None = None):
        if okf_path is None:
            okf_path = os.path.join(os.getcwd(), "okf")
        self.okf_path = Path(okf_path)
        self.chunks: list[dict[str, Any]] = []
        self._loaded = False

    def load(self) -> "OntologyRAG":
        if self._loaded:
            return self
        if not self.okf_path.is_dir():
            return self

        for md_file in sorted(self.okf_path.rglob("*.md")):
            rel = md_file.relative_to(self.okf_path)
            concept_id = str(rel.with_suffix("")).replace("\\", "/")

            text = md_file.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            full_text = f"{meta.get('title', '')}\n{body}" if meta.get("title") else body

            self.chunks.append({
                "type": meta.get("type", "concept"),
                "id": concept_id,
                "text": full_text,
                "keywords": _keywords(full_text),
                "data": meta,
            })

        self._loaded = True
        return self

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.chunks:
            self.load()
        if not self.chunks:
            return []

        q_kw = _keywords(query)
        q_lower = query.lower()

        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in self.chunks:
            score = 0.0
            for kw in q_kw:
                if kw in chunk["keywords"]:
                    score += 2.0
            for word in q_lower.split():
                if len(word) > 2 and word in chunk["text"].lower():
                    score += 1.0
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]


class OntologyRAGChat:
    def __init__(self):
        self.api_key: str | None = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)
        self.model: str | None = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
        self.rag = OntologyRAG().load()

    def ask(self, query: str, stream: bool = True):
        relevant = self.rag.retrieve(query, top_k=8)
        context_str = "\n".join(c["text"] for c in relevant)

        prompt = (
            "You are an expert P&ID (Piping & Instrumentation Diagram) analyst.\n"
            "You have access to an OKF (Open Knowledge Format) bundle containing "
            "605 P&ID symbol subclasses across 15 parent classes.\n\n"
            "Use the following knowledge context to answer the user's question.\n"
            "Be precise. Reference specific parent classes and subclasses.\n"
            "If asked about a specific symbol, list its parent class and similar symbols.\n"
            "If the question is about the ontology structure, summarize what's available.\n\n"
            f"--- Knowledge Context ---\n{context_str}\n--- End Context ---\n\n"
            f"User Question: {query}\n\n"
            "Answer:"
        )

        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
                stream=stream,
            )
        except Exception as e:
            print(f"[OntologyRAG ERROR] {e}")
            return None
