"""Tests for PIDRAG (RAG system for P&ID context)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.pid_rag import PIDRAG


class TestPIDRAG:
    SAMPLE_RESULT = {
        "nodes": [
            {
                "id": "valve_0",
                "type_key": "valve",
                "attrs": {
                    "label": "valve",
                    "Labels": "V-101",
                    "raw_id": 3,
                    "fine_class": "Gate Valve",
                    "fine_raw_id": "V-01",
                    "xmin": 100,
                    "ymin": 200,
                    "xmax": 150,
                    "ymax": 240,
                },
            },
            {
                "id": "vessel_1",
                "type_key": "vessel",
                "attrs": {
                    "label": "vessel",
                    "Labels": "T-201",
                    "raw_id": 7,
                    "fine_class": "Storage Tank",
                    "fine_raw_id": "T-01",
                    "xmin": 300,
                    "ymin": 150,
                    "xmax": 400,
                    "ymax": 250,
                },
            },
            {
                "id": "pump_2",
                "type_key": "pump",
                "attrs": {
                    "label": "pump",
                    "Labels": "P-101",
                    "raw_id": 5,
                    "fine_class": "Centrifugal Pump",
                    "fine_raw_id": "P-01",
                    "xmin": 500,
                    "ymin": 350,
                    "xmax": 570,
                    "ymax": 410,
                },
            },
        ],
        "edges": [
            {"source": "valve_0", "target": "vessel_1", "attrs": {"edge_label": "solid"}},
            {"source": "vessel_1", "target": "pump_2", "attrs": {"edge_label": "solid"}},
        ],
    }

    def test_index_creates_chunks(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        assert len(rag.chunks) > 0

    def test_index_summary_chunk(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        summary = rag.chunks[0]
        assert summary["type"] == "summary"
        assert "3 symbols" in summary["text"]

    def test_index_node_chunks(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        node_chunks = [c for c in rag.chunks if c["type"] == "node"]
        assert len(node_chunks) == 3

    def test_node_index_lookup(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        assert "valve_0" in rag.node_index
        assert rag.node_index["valve_0"]["id"] == "valve_0"

    def test_class_index_lookup(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        assert "gate valve" in rag.class_index
        assert len(rag.class_index["gate valve"]) == 1

    def test_retrieve_by_keyword(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        results = rag.retrieve("valve", top_k=3)
        assert len(results) > 0
        # At least one result should mention valve
        assert any("valve" in c["text"].lower() for c in results)

    def test_retrieve_by_count(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        results = rag.retrieve("how many symbols", top_k=5)
        assert len(results) > 0
        # Summary should be top-ranked
        assert results[0]["type"] == "summary"

    def test_retrieve_by_edges(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        results = rag.retrieve("connections", top_k=5)
        assert len(results) > 0
        # Should find edge chunks
        assert any(c["type"] == "edges" for c in results)

    def test_retrieve_empty_query(self):
        rag = PIDRAG()
        rag.index(self.SAMPLE_RESULT)
        results = rag.retrieve("", top_k=5)
        # Empty query should return some results (all score 0, but still returned)
        assert isinstance(results, list)

    def test_empty_index(self):
        rag = PIDRAG()
        rag.index({"nodes": [], "edges": []})
        assert len(rag.chunks) == 1  # Only summary chunk

    def test_extract_keywords(self):
        rag = PIDRAG()
        kw = rag._extract_keywords("How many valves are there?")
        assert "valves" in kw
        assert "how" not in kw
        assert len(kw) == 3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
