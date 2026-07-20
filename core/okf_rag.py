"""RAG engine over an OKF (Open Knowledge Format) bundle.

OKF is Google's open standard for representing knowledge as markdown files
with YAML frontmatter. This engine leverages OKF structure:
- Concepts with required `type` field
- YAML metadata for filtering and matching
- Markdown links for relationships
- Progressive disclosure (index → detail)
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


def _parse_links(body: str) -> list[str]:
    """Extract markdown links as relationships."""
    return re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)


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


class OKFRAG:
    """Reads an OKF bundle and retrieves concepts using OKF structure."""

    def __init__(self, okf_path: str | None = None):
        if okf_path is None:
            okf_path = os.path.join(os.getcwd(), "okf")
        self.okf_path = Path(okf_path)
        self.concepts: dict[str, dict[str, Any]] = {}
        self.concept_by_type: dict[str, list[str]] = {}
        self.concept_by_tag: dict[str, list[str]] = {}
        self.index_concept: dict[str, Any] | None = None
        self._loaded = False

    def load(self) -> "OKFRAG":
        if self._loaded:
            return self
        if not self.okf_path.is_dir():
            return self

        for md_file in sorted(self.okf_path.rglob("*.md")):
            rel = md_file.relative_to(self.okf_path)
            concept_id = str(rel.with_suffix("")).replace("\\", "/")

            text = md_file.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            links = _parse_links(body)

            concept = {
                "id": concept_id,
                "type": meta.get("type", "concept"),
                "title": meta.get("title", concept_id),
                "description": meta.get("description", ""),
                "tags": meta.get("tags", []),
                "body": body,
                "keywords": _keywords(body),
                "links": links,
                "meta": meta,
            }

            self.concepts[concept_id] = concept

            # Index by type
            ctype = concept["type"]
            if ctype not in self.concept_by_type:
                self.concept_by_type[ctype] = []
            self.concept_by_type[ctype].append(concept_id)

            # Index by tag
            for tag in concept["tags"]:
                if tag not in self.concept_by_tag:
                    self.concept_by_tag[tag] = []
                self.concept_by_tag[tag].append(concept_id)

            # Track index concept
            if concept_id == "index":
                self.index_concept = concept

        self._loaded = True
        return self

    def get_concept(self, concept_id: str) -> dict[str, Any] | None:
        """Get a specific concept by ID."""
        return self.concepts.get(concept_id)

    def get_by_type(self, concept_type: str) -> list[dict[str, Any]]:
        """Get all concepts of a given type."""
        ids = self.concept_by_type.get(concept_type, [])
        return [self.concepts[i] for i in ids if i in self.concepts]

    def get_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Get all concepts with a given tag."""
        ids = self.concept_by_tag.get(tag, [])
        return [self.concepts[i] for i in ids if i in self.concepts]

    def get_children(self, parent_id: str) -> list[dict[str, Any]]:
        """Get concepts that link to the given parent."""
        children = []
        for concept in self.concepts.values():
            for link_text, link_path in concept["links"]:
                if parent_id in link_path:
                    children.append(concept)
                    break
        return children

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.concepts:
            self.load()
        if not self.concepts:
            return []

        q_kw = _keywords(query)
        q_lower = query.lower()

        scored: list[tuple[float, dict[str, Any]]] = []
        for concept in self.concepts.values():
            score = 0.0

            # Exact tag match (highest weight)
            for tag in concept["tags"]:
                if tag.lower() in q_lower or tag.lower() in q_kw:
                    score += 5.0

            # Title match
            title_lower = concept["title"].lower()
            if any(w in title_lower for w in q_lower.split() if len(w) > 2):
                score += 4.0

            # Keyword match
            for kw in q_kw:
                if kw in concept["keywords"]:
                    score += 2.0

            # Body text match
            for word in q_lower.split():
                if len(word) > 2 and word in concept["body"].lower():
                    score += 1.0

            if score > 0:
                scored.append((score, concept))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def format_context(self, concepts: list[dict[str, Any]]) -> str:
        """Format concepts into context string for LLM."""
        lines = []
        for c in concepts:
            lines.append(f"### {c['title']} (type: {c['type']})")
            if c['description']:
                lines.append(f"Description: {c['description']}")
            if c['tags']:
                lines.append(f"Tags: {', '.join(c['tags'])}")
            lines.append(c['body'])
            lines.append("")
        return "\n".join(lines)


class OKFRAGChat:
    def __init__(self):
        self.api_key: str | None = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)
        self.model: str | None = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
        self.rag = OKFRAG().load()

    def ask(self, query: str, stream: bool = True):
        relevant = self.rag.retrieve(query, top_k=8)
        context_str = self.rag.format_context(relevant)

        prompt = (
            "You are an expert P&ID (Piping & Instrumentation Diagram) analyst.\n"
            "You have access to an OKF (Open Knowledge Format) knowledge bundle.\n\n"
            "OKF Structure:\n"
            "- Each concept has a 'type' field (required by OKF spec)\n"
            "- Concepts have 'title', 'description', and 'tags' in YAML frontmatter\n"
            "- Relationships are expressed via markdown links\n"
            "- The bundle contains 605 P&ID symbol subclasses across 15 parent classes\n\n"
            "Use the following knowledge context to answer the user's question.\n"
            "Be precise. Reference specific concepts, types, and tags.\n"
            "If asked about a specific symbol, list its parent class and similar symbols.\n"
            "If the question is about the knowledge structure, summarize the concept types and tags.\n\n"
            f"--- OKF Knowledge Context ---\n{context_str}\n--- End Context ---\n\n"
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
            print(f"[OKF-RAG ERROR] {e}")
            return None
