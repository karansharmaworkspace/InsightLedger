"""Industrial Knowledge Intelligence Platform - Main Orchestrator.

Ties together document ingestion, entity extraction, knowledge graph,
embeddings RAG, maintenance intelligence, and compliance intelligence.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from core.document_ingestor import IngestionManager
from core.entity_extractor import EntityExtractor
from core.knowledge_graph import KnowledgeGraph
from core.embeddings_rag import EmbeddingsRAG
from core.maintenance_intelligence import MaintenanceIntelligence, MaintenanceRecord
from core.compliance_intelligence import ComplianceIntelligence


class KnowledgePlatform:
    """Unified platform for industrial knowledge intelligence."""

    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = os.getcwd()
        self.base_dir = Path(base_dir)

        self.ingestion = IngestionManager(str(self.base_dir / "storage" / "documents"))
        self.extractor = EntityExtractor()
        self.kg = KnowledgeGraph(str(self.base_dir / "storage" / "knowledge_graph.json"))
        self.rag = EmbeddingsRAG(storage_path=str(self.base_dir / "storage" / "embeddings.json"))
        self.maintenance = MaintenanceIntelligence()
        self.compliance = ComplianceIntelligence()

    def ingest_document(self, file_path: str) -> dict[str, Any]:
        """Ingest a single document: extract, index, build knowledge graph."""
        chunks = self.ingestion.ingest_file(file_path)
        if not chunks:
            return {"status": "error", "message": "No content extracted"}

        # Extract entities from all chunks
        all_entities = []
        for chunk in chunks:
            entities = self.extractor.extract(chunk["content"])
            all_entities.extend(entities)

            # Add to embeddings RAG
            self.rag.add_chunks([{
                "content": chunk["content"],
                "source": chunk["source"],
                "doc_type": chunk["doc_type"],
                "page": chunk.get("page"),
            }])

            # Add to knowledge graph
            for entity in entities:
                self.kg.add_entity(
                    entity_type=entity.entity_type,
                    value=entity.value,
                    source=chunk["source"],
                    context=entity.context,
                    confidence=entity.confidence,
                )

        # Add to compliance analysis
        full_text = "\n".join(c["content"] for c in chunks)
        self.compliance.add_document({
            "content": full_text,
            "source": file_path,
            "doc_type": chunks[0]["doc_type"] if chunks else "unknown",
        })

        # Check for maintenance records
        for chunk in chunks:
            content_lower = chunk["content"].lower()
            if any(w in content_lower for w in ["work order", "maintenance", "failure", "breakdown"]):
                self.maintenance.add_records_from_text(chunk["content"], file_path)

        # Build relationships between entities
        self._build_entity_relationships(file_path, all_entities)

        return {
            "status": "success",
            "chunks": len(chunks),
            "entities": len(all_entities),
            "entity_types": list(set(e.entity_type for e in all_entities)),
        }

    def ingest_directory(self, dir_path: str) -> dict[str, Any]:
        """Ingest all supported documents from a directory."""
        chunks = self.ingestion.ingest_directory(dir_path)
        if not chunks:
            return {"status": "error", "message": "No documents found"}

        # Process each chunk
        all_entities = []
        for chunk in chunks:
            entities = self.extractor.extract(chunk["content"])
            all_entities.extend(entities)

            self.rag.add_chunks([{
                "content": chunk["content"],
                "source": chunk["source"],
                "doc_type": chunk["doc_type"],
                "page": chunk.get("page"),
            }])

            for entity in entities:
                self.kg.add_entity(
                    entity_type=entity.entity_type,
                    value=entity.value,
                    source=chunk["source"],
                    context=entity.context,
                    confidence=entity.confidence,
                )

            # Check for maintenance/compliance
            content_lower = chunk["content"].lower()
            if any(w in content_lower for w in ["work order", "maintenance", "failure"]):
                self.maintenance.add_records_from_text(chunk["content"], chunk["source"])

            self.compliance.add_document({
                "content": chunk["content"],
                "source": chunk["source"],
                "doc_type": chunk["doc_type"],
            })

        return {
            "status": "success",
            "total_chunks": len(chunks),
            "total_entities": len(all_entities),
        }

    def _build_entity_relationships(self, source: str, entities: list):
        """Build edges between entities that appear in the same document."""
        # Group by type
        by_type: dict[str, list] = {}
        for e in entities:
            if e.entity_type not in by_type:
                by_type[e.entity_type] = []
            by_type[e.entity_type].append(e)

        # Create edges between co-occurring entities
        tags = by_type.get("equipment_tag", [])
        params = by_type.get("process_parameter", [])
        dates = by_type.get("date", [])

        # Equipment -> Parameter relationships
        for tag in tags:
            for param in params:
                self.kg.add_edge(
                    f"equipment_tag:{tag.value}",
                    f"process_parameter:{param.value}",
                    relation="has_parameter",
                    weight=0.8,
                )

            # Equipment -> Date relationships
            for date in dates:
                self.kg.add_edge(
                    f"equipment_tag:{tag.value}",
                    f"date:{date.value}",
                    relation="referenced_on",
                    weight=0.6,
                )

    def query(self, question: str) -> dict[str, Any]:
        """Answer a question using RAG + knowledge graph."""
        # Get semantic search results
        rag_results = self.rag.retrieve(question, top_k=5)

        # Check knowledge graph for entity matches
        kg_context = []
        tags = re.findall(r'\b[A-Z]{1,4}-\d{3,4}[A-Z]?\b', question)
        for tag in tags:
            network = self.kg.get_entity_network(tag, depth=1)
            if network["nodes"]:
                kg_context.append(f"Equipment {tag} network: {len(network['nodes'])} connected entities")

        # Combine context
        context_parts = [r["content"] for r in rag_results]
        if kg_context:
            context_parts.extend(kg_context)

        return {
            "answer_context": "\n\n".join(context_parts),
            "sources": list(set(r["source"] for r in rag_results)),
            "rag_results": rag_results,
            "kg_matches": kg_context,
        }

    def get_maintenance_analysis(self, equipment_tag: str) -> dict[str, Any]:
        """Get maintenance intelligence for equipment."""
        history = self.maintenance.get_equipment_history(equipment_tag)
        patterns = self.maintenance.get_failure_patterns()
        recommendations = self.maintenance.get_maintenance_recommendations(equipment_tag)

        return {
            "equipment_tag": equipment_tag,
            "history": history,
            "patterns": patterns,
            "recommendations": recommendations,
        }

    def get_compliance_status(self) -> dict[str, Any]:
        """Get compliance status of entire corpus."""
        return self.compliance.analyze_corpus()

    def get_audit_package(self) -> dict[str, Any]:
        """Generate compliance audit package."""
        return self.compliance.get_audit_package()

    def get_knowledge_graph_stats(self) -> dict[str, Any]:
        """Get knowledge graph statistics."""
        return self.kg.get_stats()

    def get_rag_stats(self) -> dict[str, Any]:
        """Get embeddings RAG statistics."""
        return self.rag.get_stats()
