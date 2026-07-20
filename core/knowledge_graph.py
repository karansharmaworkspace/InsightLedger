"""Knowledge graph for linking entities across documents.

Stores entities as nodes and relationships as edges.
Supports queries by entity type, value, and document source.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


class KnowledgeGraph:
    """In-memory knowledge graph with JSON persistence."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "storage", "knowledge_graph.json")
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._node_index: dict[str, set[str]] = defaultdict(set)  # value -> node_ids
        self._type_index: dict[str, set[str]] = defaultdict(set)  # type -> node_ids
        self._source_index: dict[str, set[str]] = defaultdict(set)  # source -> node_ids
        self._dirty = False  # ponytail: batch saves, flush() for explicit persistence

        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.nodes = data.get("nodes", {})
            self.edges = data.get("edges", [])
            self._rebuild_indexes()
        except Exception as e:
            print(f"[KG] Load error: {e}")

    def _rebuild_indexes(self):
        self._node_index.clear()
        self._type_index.clear()
        self._source_index.clear()
        for nid, node in self.nodes.items():
            self._node_index[node["value"].lower()].add(nid)
            self._type_index[node["type"]].add(nid)
            for src in node.get("sources", []):
                self._source_index[src].add(nid)

    def save(self):
        data = {"nodes": self.nodes, "edges": self.edges}
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._dirty = False

    def flush(self):
        """Persist to disk if there are pending changes."""
        if self._dirty:
            self.save()

    def add_entity(
        self,
        entity_type: str,
        value: str,
        source: str,
        context: str = "",
        confidence: float = 0.8,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add an entity node. Returns node ID."""
        # Check if node with same type+value exists
        existing = self.find_entity(entity_type, value)
        if existing:
            # Merge: add new source
            if source not in existing["sources"]:
                existing["sources"].append(source)
            if context and context not in existing.get("contexts", []):
                existing.setdefault("contexts", []).append(context)
            self.save()
            return existing["id"]

        nid = f"{entity_type}:{value}"
        node = {
            "id": nid,
            "type": entity_type,
            "value": value,
            "sources": [source],
            "contexts": [context] if context else [],
            "confidence": confidence,
            "metadata": metadata or {},
        }
        self.nodes[nid] = node
        self._node_index[value.lower()].add(nid)
        self._type_index[entity_type].add(nid)
        self._source_index[source].add(nid)
        self._dirty = True
        return nid

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ):
        """Add a relationship edge."""
        # Check if edge exists
        for edge in self.edges:
            if edge["source"] == source_id and edge["target"] == target_id and edge["relation"] == relation:
                edge["weight"] = max(edge["weight"], weight)
                self._dirty = True
                return

        self.edges.append({
            "source": source_id,
            "target": target_id,
            "relation": relation,
            "weight": weight,
            "metadata": metadata or {},
        })
        self._dirty = True

    def find_entity(self, entity_type: str, value: str) -> dict[str, Any] | None:
        """Find entity by type and value."""
        nid = f"{entity_type}:{value}"
        return self.nodes.get(nid)

    def find_by_value(self, value: str) -> list[dict[str, Any]]:
        """Find all nodes matching a value (case-insensitive)."""
        value_lower = value.lower()
        nids = self._node_index.get(value_lower, set())
        return [self.nodes[nid] for nid in nids if nid in self.nodes]

    def find_by_type(self, entity_type: str) -> list[dict[str, Any]]:
        """Find all nodes of a given type."""
        nids = self._type_index.get(entity_type, set())
        return [self.nodes[nid] for nid in nids if nid in self.nodes]

    def find_by_source(self, source: str) -> list[dict[str, Any]]:
        """Find all nodes from a given source document."""
        nids = self._source_index.get(source, set())
        return [self.nodes[nid] for nid in nids if nid in self.nodes]

    def get_neighbors(self, node_id: str, relation: str | None = None) -> list[dict[str, Any]]:
        """Get neighboring nodes, optionally filtered by relation."""
        neighbors = []
        for edge in self.edges:
            target_nid = None
            if edge["source"] == node_id:
                target_nid = edge["target"]
            elif edge["target"] == node_id:
                target_nid = edge["source"]

            if target_nid and target_nid in self.nodes:
                if relation is None or edge["relation"] == relation:
                    neighbor = dict(self.nodes[target_nid])
                    neighbor["_relation"] = edge["relation"]
                    neighbor["_edge_weight"] = edge["weight"]
                    neighbors.append(neighbor)
        return neighbors

    def get_entity_network(self, value: str, depth: int = 2) -> dict[str, Any]:
        """Get the network around an entity value."""
        nodes = self.find_by_value(value)
        if not nodes:
            return {"nodes": {}, "edges": []}

        visited = set()
        result_nodes = {}
        result_edges = []

        def traverse(node_id: str, current_depth: int):
            if current_depth > depth or node_id in visited:
                return
            visited.add(node_id)
            if node_id in self.nodes:
                result_nodes[node_id] = self.nodes[node_id]
            for edge in self.edges:
                if edge["source"] == node_id or edge["target"] == node_id:
                    result_edges.append(edge)
                    other = edge["target"] if edge["source"] == node_id else edge["source"]
                    traverse(other, current_depth + 1)

        for node in nodes:
            traverse(node["id"], 0)

        return {"nodes": result_nodes, "edges": result_edges}

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        type_counts = {}
        for node in self.nodes.values():
            t = node["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "types": type_counts,
            "sources": len(self._source_index),
        }

    def merge_graph(self, other: "KnowledgeGraph"):
        """Merge another graph into this one."""
        for nid, node in other.nodes.items():
            if nid in self.nodes:
                # Merge sources
                for src in node.get("sources", []):
                    if src not in self.nodes[nid]["sources"]:
                        self.nodes[nid]["sources"].append(src)
            else:
                self.nodes[nid] = node

        for edge in other.edges:
            exists = any(
                e["source"] == edge["source"]
                and e["target"] == edge["target"]
                and e["relation"] == edge["relation"]
                for e in self.edges
            )
            if not exists:
                self.edges.append(edge)

        self._rebuild_indexes()
        self.save()
