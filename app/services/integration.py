"""
Integration Health Check - System-wide health and readiness
"""
from typing import Dict, Any
from pathlib import Path

from app.services.vector_search import VectorSearchService
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.rag_engine import RAGEngine
from app.services.maintenance import MaintenanceService
from app.services.compliance import ComplianceService


class HealthChecker:
    """System-wide health checks"""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = storage_dir

    def check_all(self) -> Dict[str, Any]:
        results = {
            "status": "healthy",
            "checks": {},
        }

        checks = [
            ("vector_search", self._check_vector_search),
            ("knowledge_graph", self._check_knowledge_graph),
            ("rag_engine", self._check_rag_engine),
            ("maintenance", self._check_maintenance),
            ("compliance", self._check_compliance),
            ("storage", self._check_storage),
        ]

        for name, check_fn in checks:
            try:
                result = check_fn()
                result["status"] = "ok"
                results["checks"][name] = result
            except Exception as e:
                results["checks"][name] = {"status": "error", "error": str(e)}
                results["status"] = "degraded"

        return results

    def _check_vector_search(self) -> Dict[str, Any]:
        svc = VectorSearchService(self.storage_dir)
        stats = svc.get_stats()
        return {"chunks_indexed": stats.get("total_chunks", 0)}

    def _check_knowledge_graph(self) -> Dict[str, Any]:
        svc = KnowledgeGraphService(self.storage_dir)
        stats = svc.get_stats()
        return {"nodes": stats.get("total_nodes", 0), "edges": stats.get("total_edges", 0)}

    def _check_rag_engine(self) -> Dict[str, Any]:
        svc = RAGEngine(self.storage_dir)
        cache_stats = svc.get_cache_stats()
        return {"cache_entries": cache_stats.get("total_entries", 0)}

    def _check_maintenance(self) -> Dict[str, Any]:
        svc = MaintenanceService(self.storage_dir)
        tasks = svc.get_tasks(status="pending")
        return {"pending_tasks": len(tasks)}

    def _check_compliance(self) -> Dict[str, Any]:
        svc = ComplianceService(self.storage_dir)
        status = svc.get_compliance_status()
        return {"compliance_summary": status}

    def _check_storage(self) -> Dict[str, Any]:
        storage = Path(self.storage_dir)
        dirs = ["documents", "vectors", "knowledge_graph", "cache", "maintenance", "compliance"]
        existing = [d for d in dirs if (storage / d).exists()]
        return {"storage_dirs": existing, "total_dirs": len(dirs)}
