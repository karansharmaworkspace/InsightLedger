from __future__ import annotations

import json
import os
import re
from typing import Any

from groq import Groq
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


class OKFRAG:
    def __init__(self, ontology_path: str | None = None):
        if ontology_path is None:
            ontology_path = os.path.join(os.getcwd(), "assets", "legend_classification.json")
        self.ontology_path = ontology_path
        self.classes: dict[str, dict[str, Any]] = {}
        self.chunks: list[dict[str, Any]] = []
        self._loaded = False

    def load(self):
        if self._loaded:
            return self
        if not os.path.exists(self.ontology_path):
            return self

        with open(self.ontology_path, "r") as f:
            raw = json.load(f)

        legend = raw.get("legend_classification", {})
        self.classes = legend.get("classes", {})

        self.chunks = []
        for parent_name, info in self.classes.items():
            subclasses = info.get("subclasses", [])
            count = len(subclasses)
            sub_list = ", ".join(s.replace("_", " ") for s in subclasses[:30])
            if count > 30:
                sub_list += f", ... ({count - 30} more)"

            self.chunks.append({
                "type": "parent_class",
                "id": parent_name,
                "text": (
                    f"Parent class: {parent_name}\n"
                    f"Subclass count: {count}\n"
                    f"Subclasses: {sub_list}"
                ),
                "keywords": self._keywords(f"{parent_name} {' '.join(subclasses)}"),
                "data": {"parent": parent_name, "subclasses": subclasses}
            })

            for sub in subclasses:
                display = sub.replace("_", " ")
                self.chunks.append({
                    "type": "subclass",
                    "id": sub,
                    "text": f"{display} is a subclass of {parent_name}",
                    "keywords": self._keywords(f"{sub} {parent_name} {display}"),
                    "data": {"parent": parent_name, "subclass": sub, "display": display}
                })

        meta = legend.get("metadata", {})
        summary = (
            f"OKF Ontology: {meta.get('total_classes', len(self.classes))} parent classes, "
            f"{meta.get('total_subclasses', 0)} subclasses. "
            f"Parents: {', '.join(self.classes.keys())}."
        )
        self.chunks.insert(0, {
            "type": "ontology_summary",
            "id": "ontology_summary",
            "text": summary,
            "keywords": self._keywords(summary),
            "data": meta
        })

        self._loaded = True
        return self

    def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.chunks:
            self.load()
        if not self.chunks:
            return []

        q_kw = self._keywords(query)
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
        results = [c for _, c in scored[:top_k]]

        if not results:
            results = [c for c in self.chunks if c["type"] == "ontology_summary"][:1]

        return results

    def _keywords(self, text: str) -> set[str]:
        text = re.sub(r"[^a-z0-9_\s]", " ", text.lower())
        stops = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "and", "but", "or",
            "not", "so", "this", "that", "these", "those", "none",
        }
        return {w for w in text.split() if len(w) > 2 and w not in stops}


class OKFRAGChat:
    def __init__(self):
        self.api_key: str | None = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)
        self.model: str | None = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
        self.rag = OKFRAG().load()

    def ask(self, query: str, stream: bool = True):
        relevant = self.rag.retrieve(query, top_k=8)
        context_str = "\n".join(c["text"] for c in relevant)

        prompt = (
            "You are an expert P&ID (Piping & Instrumentation Diagram) analyst.\n"
            "You have access to an OKF (Ontology Knowledge Framework) containing "
            "605 P&ID symbol subclasses across 15 parent classes.\n\n"
            "Use the following ontology context to answer the user's question.\n"
            "Be precise. Reference specific parent classes and subclasses.\n"
            "If asked about a specific symbol, list its parent class and similar symbols.\n"
            "If the question is about the ontology structure, summarize what's available.\n\n"
            f"--- OKF Context ---\n{context_str}\n--- End Context ---\n\n"
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
