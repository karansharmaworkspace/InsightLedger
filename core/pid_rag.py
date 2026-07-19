from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any


class PIDRAG:
    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self.node_index: dict[str, dict[str, Any]] = {}
        self.class_index: dict[str, list[dict[str, Any]]] = {}

    def index(self, result_json: dict[str, Any]) -> None:
        self.chunks = []
        self.node_index = {}
        self.class_index = {}

        nodes = result_json.get("nodes", [])
        edges = result_json.get("edges", [])

        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "classes": Counter(),
            "fine_classes": Counter(),
            "labels": []
        }

        for node in nodes:
            attrs = node.get("attrs", {})
            node_id = node.get("id", "")
            label = attrs.get("label", "")
            fine = attrs.get("fine_class", "")
            ocr = attrs.get("Labels", "N/A")
            x1 = attrs.get("xmin", 0)
            y1 = attrs.get("ymin", 0)
            x2 = attrs.get("xmax", 0)
            y2 = attrs.get("ymax", 0)

            stats["classes"][label] += 1
            if fine:
                stats["fine_classes"][fine] += 1
            if ocr and ocr != "N/A":
                stats["labels"].append({"id": node_id, "label": ocr, "class": fine or label})

            chunk = {
                "type": "node",
                "id": node_id,
                "text": f"{node_id}: class={label}, fine={fine or 'none'}, labels={ocr}, pos=({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})",
                "keywords": self._extract_keywords(f"{node_id} {label} {fine} {ocr}"),
                "data": node
            }
            self.chunks.append(chunk)
            self.node_index[node_id.lower()] = chunk
            if fine:
                self.class_index.setdefault(fine.lower(), []).append(chunk)
            self.class_index.setdefault(label.lower(), []).append(chunk)

        stats_text = (
            f"Summary: {stats['total_nodes']} symbols, {stats['total_edges']} connections. "
            f"Classes: {', '.join(f'{k}({v})' for k, v in stats['classes'].most_common(10))}. "
            f"Fine classes: {', '.join(f'{k}({v})' for k, v in stats['fine_classes'].most_common(10))}."
        )
        self.chunks.insert(0, {
            "type": "summary",
            "id": "summary",
            "text": stats_text,
            "keywords": self._extract_keywords(stats_text),
            "data": {"stats": dict(stats["classes"]), "fine_stats": dict(stats["fine_classes"])}
        })

        if stats["labels"]:
            labels_text = "Labels found: " + ", ".join(
                f"{l['id']}={l['label']}" for l in stats["labels"][:50]
            )
            self.chunks.insert(1, {
                "type": "labels",
                "id": "all_labels",
                "text": labels_text,
                "keywords": self._extract_keywords(labels_text),
                "data": stats["labels"]
            })

        for i in range(0, len(edges), 10):
            batch = edges[i:i+10]
            edge_text = "Connections: " + ", ".join(
                f"{e.get('source','?')}→{e.get('target','?')}" for e in batch
            )
            self.chunks.append({
                "type": "edges",
                "id": f"edges_{i}",
                "text": edge_text,
                "keywords": self._extract_keywords(edge_text),
                "data": batch
            })

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_keywords = self._extract_keywords(query)
        query_lower = query.lower()

        # Multi-language query type hints — covers top UI languages
        _count_words = {"how many", "count", "total", "number of", "quantos", "cuantos",
                        "多少个", "いくつ", "몇", "كم", "कितने"}
        _connect_words = {"connect", "edge", "link", "connection", "conecta", "conectar",
                          "连接", "接続", "연결", "ربط", "जोड़"}
        _label_words  = {"label", "text", "ocr", "tag", "etiqueta", "texto",
                         "标签", "テキスト", "레이블", "نص", "लेबल"}

        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in self.chunks:
            score = 0.0

            for kw in query_keywords:
                if kw in chunk["keywords"]:
                    score += 2.0

            chunk_lower = chunk["text"].lower()
            for word in query_lower.split():
                if len(word) > 2 and word in chunk_lower:
                    score += 1.5

            if any(c.isdigit() for c in query) and any(c.isdigit() for c in chunk["text"]):
                query_nums = re.findall(r'\d+', query)
                chunk_nums = re.findall(r'\d+', chunk["text"])
                for qn in query_nums:
                    if qn in chunk_nums:
                        score += 3.0

            if any(w in query_lower for w in _count_words):
                if chunk["type"] == "summary":
                    score += 5.0

            if any(w in query_lower for w in _connect_words):
                if chunk["type"] == "edges":
                    score += 4.0

            if any(w in query_lower for w in _label_words):
                if chunk["type"] == "labels":
                    score += 4.0

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [chunk for _, chunk in scored[:top_k]]

        # Fallback: if nothing scored, return the summary chunk so the LLM gets something
        if not results:
            for chunk in self.chunks:
                if chunk["type"] == "summary":
                    results.append(chunk)
                    break

        return results

    def _extract_keywords(self, text: str) -> set[str]:
        text = text.lower()
        text = re.sub(r'[^a-z0-9_\s]', ' ', text)
        words = text.split()
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'shall', 'can',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after', 'and',
                     'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
                     'neither', 'each', 'every', 'all', 'any', 'few', 'more',
                     'most', 'other', 'some', 'such', 'no', 'only', 'own', 'same',
                     'than', 'too', 'very', 'just', 'because', 'if', 'when', 'where',
                     'how', 'what', 'which', 'who', 'whom', 'this', 'that', 'these',
                     'those', 'none'}
        return set(w for w in words if len(w) > 2 and w not in stopwords)
