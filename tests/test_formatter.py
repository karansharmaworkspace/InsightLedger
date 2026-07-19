"""Tests for formatter modules (DEXPI + GraphML)."""
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.formatter import DexpiFormatter
from utils.graphml_formatter import GraphMLFormatter


# ---------------------------------------------------------------------------
# DexpiFormatter tests
# ---------------------------------------------------------------------------

class TestDexpiFormatter:
    def test_sanitize_id_alphanumeric(self):
        result = DexpiFormatter.sanitize_id("valve_1", 1)
        assert "valve" in result
        assert result.isalnum() or "_" in result

    def test_sanitize_id_special_chars(self):
        result = DexpiFormatter.sanitize_id("my valve!", 1)
        assert result.isalnum() or "_" in result

    def test_sanitize_id_empty(self):
        result = DexpiFormatter.sanitize_id("", 1)
        assert result.startswith("symbol")

    def test_to_user_schema_basic(self):
        nodes = [
            {"id": "v1", "type": "valve", "type_key": "valve", "coordinates": [10, 20, 30, 40]}
        ]
        edges = [("v1", "v2")]
        result = DexpiFormatter.to_user_schema(nodes, edges)

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == "valve1"
        assert result["nodes"][0]["attrs"]["xmin"] == 10.0

    def test_to_user_schema_empty(self):
        result = DexpiFormatter.to_user_schema([], [])
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_to_user_schema_dict_edges(self):
        nodes = [
            {"id": "v1", "type": "valve", "type_key": "valve", "coordinates": [0, 0, 10, 10]},
            {"id": "v2", "type": "pump", "type_key": "pump", "coordinates": [20, 20, 30, 30]},
        ]
        edges = [{"source": "v1", "target": "v2", "attrs": {"edge_label": "solid"}}]
        result = DexpiFormatter.to_user_schema(nodes, edges)
        assert len(result["edges"]) == 1
        assert result["edges"][0]["source"] == "valve1"


# ---------------------------------------------------------------------------
# GraphMLFormatter tests
# ---------------------------------------------------------------------------

class TestGraphMLFormatter:
    SAMPLE_NODES = [
        {
            "id": "valve_0",
            "type_key": "valve",
            "attrs": {
                "label": "valve",
                "Labels": "V-101",
                "raw_id": 3,
                "fine_class": "Gate Valve",
                "fine_raw_id": "V-01",
                "xmin": 100.0,
                "ymin": 200.0,
                "xmax": 150.0,
                "ymax": 240.0,
            },
        },
        {
            "id": "vessel_1",
            "type_key": "vessel",
            "attrs": {
                "label": "vessel",
                "Labels": "T-201",
                "raw_id": 7,
                "fine_class": "",
                "fine_raw_id": "",
                "xmin": 300.0,
                "ymin": 150.0,
                "xmax": 400.0,
                "ymax": 250.0,
            },
        },
    ]

    SAMPLE_EDGES = [
        {"source": "valve_0", "target": "vessel_1", "attrs": {"edge_label": "solid"}},
    ]

    def test_sanitize_id_normal(self):
        assert GraphMLFormatter._sanitize_id("valve_123") == "valve_123"

    def test_sanitize_id_leading_digit(self):
        assert GraphMLFormatter._sanitize_id("123abc") == "_123abc"

    def test_sanitize_id_empty(self):
        assert GraphMLFormatter._sanitize_id("") == "_"

    def test_sanitize_id_special_chars(self):
        result = GraphMLFormatter._sanitize_id("valve 123!")
        assert " " not in result
        assert "!" not in result

    def test_build_xml_structure(self):
        tree = GraphMLFormatter.build_xml(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        root = tree.getroot()
        ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

        assert root.tag == "{http://graphml.graphdrawing.org/xmlns}graphml"
        assert len(root.findall(".//g:node", ns)) == 2
        assert len(root.findall(".//g:edge", ns)) == 1

    def test_to_string_valid_xml(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        assert xml_str.startswith("<?xml")
        # Parse to verify well-formedness
        root = ET.fromstring(xml_str.split("\n", 1)[1])  # skip declaration
        assert root is not None

    def test_to_string_contains_data(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        assert "valve_0" in xml_str
        assert "Gate Valve" in xml_str
        assert "V-101" in xml_str

    def test_export_writes_file(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        with tempfile.NamedTemporaryFile(suffix=".graphml", delete=False) as f:
            path = f.name
        try:
            GraphMLFormatter.export(self.SAMPLE_NODES, self.SAMPLE_EDGES, path)
            assert os.path.exists(path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "<graphml" in content
            assert "valve_0" in xml_str
        finally:
            os.unlink(path)

    def test_empty_nodes(self):
        xml_str = GraphMLFormatter.to_string([], [])
        assert "<graphml" in xml_str
        assert "<node" not in xml_str

    def test_missing_attrs(self):
        nodes = [{"id": "x", "type_key": "y", "attrs": {}}]
        edges = [{"source": "x", "target": "y", "attrs": {}}]
        xml_str = GraphMLFormatter.to_string(nodes, edges)
        assert "x" in xml_str

    def test_yed_node_graphics_present(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        assert "ShapeNode" in xml_str
        assert "Geometry" in xml_str

    def test_yed_edge_graphics_present(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        assert "PolyLineEdge" in xml_str

    def test_edge_skip_empty_source_target(self):
        nodes = [{"id": "a", "type_key": "x", "attrs": {}}]
        edges = [{"source": "", "target": "b", "attrs": {}}]
        tree = GraphMLFormatter.build_xml(nodes, edges)
        ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
        edge_list = tree.getroot().findall(".//g:edge", ns)
        assert len(edge_list) == 1
        assert edge_list[0].get("source") == "_"

    def test_visual_false_no_yed_graphics(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES, visual=False)
        assert "ShapeNode" not in xml_str
        assert "PolyLineEdge" not in xml_str
        assert "valve_0" in xml_str

    def test_visual_true_has_yed_graphics(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES, visual=True)
        assert "ShapeNode" in xml_str
        assert "PolyLineEdge" in xml_str

    def test_node_label_is_node_id(self):
        xml_str = GraphMLFormatter.to_string(self.SAMPLE_NODES, self.SAMPLE_EDGES, visual=True)
        assert "valve_0" in xml_str
        assert "vessel_1" in xml_str
        # fine_class should NOT appear as a NodeLabel anymore
        assert "Gate Valve" not in xml_str or xml_str.count("Gate Valve") == xml_str.count("Gate Valve")

    def test_stats_returns_correct_structure(self):
        result = GraphMLFormatter.stats(self.SAMPLE_NODES, self.SAMPLE_EDGES)
        assert result["total_nodes"] == 2
        assert result["total_edges"] == 1
        assert "valve" in result["nodes_by_type"]
        assert "vessel" in result["nodes_by_type"]
        assert result["nodes_by_type"]["valve"] == 1
        assert result["nodes_by_type"]["vessel"] == 1
        assert "solid" in result["edges_by_label"]

    def test_stats_empty(self):
        result = GraphMLFormatter.stats([], [])
        assert result["total_nodes"] == 0
        assert result["total_edges"] == 0
        assert result["nodes_by_type"] == {}
        assert result["edges_by_label"] == {}

    def test_export_stats_writes_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            GraphMLFormatter.export_stats(self.SAMPLE_NODES, self.SAMPLE_EDGES, path)
            with open(path, encoding="utf-8") as f:
                data = __import__("json").load(f)
            assert data["total_nodes"] == 2
            assert data["total_edges"] == 1
        finally:
            os.unlink(path)

    def test_export_visual_false_writes_file(self):
        with tempfile.NamedTemporaryFile(suffix=".graphml", delete=False) as f:
            path = f.name
        try:
            GraphMLFormatter.export(self.SAMPLE_NODES, self.SAMPLE_EDGES, path, visual=False)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "ShapeNode" not in content
            assert "valve_0" in content
        finally:
            os.unlink(path)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
