"""
Knowledge Graph Service
Builds and queries OKF knowledge graph using NetworkX.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import networkx as nx

from app.services.entity_extraction import (
    EntityExtractionService, ExtractedEntities, Equipment, ProcessParameter, RegulatoryRef
)


class KnowledgeGraphService:
    """Service for building and querying the OKF knowledge graph."""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.graph_dir = self.storage_dir / "knowledge_graph"
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self.entity_service = EntityExtractionService()
        self._graph = None

    @property
    def graph(self) -> nx.DiGraph:
        if self._graph is None:
            self._graph = self._load_graph()
        return self._graph

    def _load_graph(self) -> nx.DiGraph:
        graph_file = self.graph_dir / "graph.json"
        if graph_file.exists():
            data = json.loads(graph_file.read_text(encoding="utf-8"))
            return nx.node_link_graph(data)
        return nx.DiGraph()

    def _save_graph(self):
        data = nx.node_link_data(self.graph)
        (self.graph_dir / "graph.json").write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8"
        )

    def add_equipment(self, equipment: Equipment, document_id: str = ""):
        """Add equipment node to graph."""
        node_id = f"equipment:{equipment.id}"
        self.graph.add_node(node_id, **{
            "type": "equipment",
            "tag": equipment.tag,
            "name": equipment.name,
            "equipment_type": equipment.equipment_type,
            "location": equipment.location,
            "created_at": datetime.now().isoformat(),
        })

        if document_id:
            doc_node = f"document:{document_id}"
            if doc_node not in self.graph:
                self.graph.add_node(doc_node, type="document", id=document_id)
            self.graph.add_edge(doc_node, node_id, relation="contains")

    def add_parameter(self, param: ProcessParameter, equipment_tag: str = ""):
        """Add process parameter node and link to equipment."""
        param_id = f"param:{param.name}:{param.value}_{param.unit}"
        self.graph.add_node(param_id, **{
            "type": "parameter",
            "name": param.name,
            "value": param.value,
            "unit": param.unit,
        })

        if equipment_tag:
            eq_node = f"equipment:{equipment_tag.lower()}"
            if eq_node in self.graph:
                self.graph.add_edge(eq_node, param_id, relation="has_parameter")

    def add_regulation(self, reg: RegulatoryRef, equipment_tag: str = ""):
        """Add regulation node and link to equipment."""
        reg_id = f"regulation:{reg.standard}:{reg.section}"
        self.graph.add_node(reg_id, **{
            "type": "regulation",
            "standard": reg.standard,
            "section": reg.section,
            "description": reg.description,
        })

        if equipment_tag:
            eq_node = f"equipment:{equipment_tag.lower()}"
            if eq_node in self.graph:
                self.graph.add_edge(eq_node, reg_id, relation="must_comply")

    def add_procedure(self, procedure_id: str, name: str, steps: List[str], equipment_tags: List[str]):
        """Add procedure node and link to equipment."""
        node_id = f"procedure:{procedure_id}"
        self.graph.add_node(node_id, **{
            "type": "procedure",
            "name": name,
            "steps": steps,
        })

        for tag in equipment_tags:
            eq_node = f"equipment:{tag.lower()}"
            if eq_node in self.graph:
                self.graph.add_edge(node_id, eq_node, relation="involves")

    def add_incident(self, incident_id: str, description: str, equipment_tags: List[str], date: str = ""):
        """Add incident node and link to equipment."""
        node_id = f"incident:{incident_id}"
        self.graph.add_node(node_id, **{
            "type": "incident",
            "description": description,
            "date": date,
        })

        for tag in equipment_tags:
            eq_node = f"equipment:{tag.lower()}"
            if eq_node in self.graph:
                self.graph.add_edge(node_id, eq_node, relation="affected")

    def process_document(self, text: str, document_id: str):
        """Extract entities from text and add to knowledge graph."""
        entities = self.entity_service.extract_all(text, document_id)

        for eq in entities.equipment:
            self.add_equipment(eq, document_id)

        equipment_tags = [eq.tag for eq in entities.equipment]
        for param in entities.parameters:
            self.add_parameter(param, equipment_tags[0] if equipment_tags else "")

        for reg in entities.regulations:
            self.add_regulation(reg, equipment_tags[0] if equipment_tags else "")

        self._save_graph()

        return {
            "equipment_count": len(entities.equipment),
            "parameter_count": len(entities.parameters),
            "regulation_count": len(entities.regulations),
            "personnel_count": len(entities.personnel),
            "date_count": len(entities.dates),
        }

    def get_equipment(self, equipment_id: Optional[str] = None) -> List[Dict]:
        """Get equipment from knowledge graph."""
        if equipment_id:
            node_id = f"equipment:{equipment_id.lower()}"
            if node_id in self.graph:
                return [self.graph.nodes[node_id]]
            return []

        return [
            data for node, data in self.graph.nodes(data=True)
            if data.get("type") == "equipment"
        ]

    def get_connected(self, node_id: str) -> Dict[str, List[Dict]]:
        """Get nodes connected to a given node."""
        if node_id not in self.graph:
            return {"incoming": [], "outgoing": []}

        incoming = []
        for pred in self.graph.predecessors(node_id):
            edge_data = self.graph.edges[pred, node_id]
            node_data = self.graph.nodes[pred]
            incoming.append({**node_data, "relation": edge_data.get("relation", "")})

        outgoing = []
        for succ in self.graph.successors(node_id):
            edge_data = self.graph.edges[node_id, succ]
            node_data = self.graph.nodes[succ]
            outgoing.append({**node_data, "relation": edge_data.get("relation", "")})

        return {"incoming": incoming, "outgoing": outgoing}

    def search(self, query: str) -> List[Dict]:
        """Search across knowledge graph nodes."""
        query_lower = query.lower()
        results = []

        for node_id, data in self.graph.nodes(data=True):
            searchable = " ".join(str(v) for v in data.values()).lower()
            if query_lower in searchable:
                results.append({"id": node_id, **data})

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get knowledge graph statistics."""
        node_types = {}
        for _, data in self.graph.nodes(data=True):
            ntype = data.get("type", "unknown")
            node_types[ntype] = node_types.get(ntype, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
        }

    def to_json(self) -> Dict:
        """Export graph as JSON for visualization."""
        return nx.node_link_data(self.graph)
