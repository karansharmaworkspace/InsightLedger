"""Tests for TopologyEngine (line detection and connectivity inference)."""
import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.topology_engine import TopologyEngine


class TestTopologyEngine:
    def test_dist_to_bbox_inside(self):
        """Point inside bbox should have distance 0."""
        bbox = (100, 100, 200, 200)
        point = (150, 150)
        assert TopologyEngine._dist_to_bbox(point, bbox) == 0.0

    def test_dist_to_bbox_outside_horizontal(self):
        """Point outside horizontally."""
        bbox = (100, 100, 200, 200)
        point = (250, 150)
        dist = TopologyEngine._dist_to_bbox(point, bbox)
        assert abs(dist - 50.0) < 1e-6

    def test_dist_to_bbox_outside_vertical(self):
        """Point outside vertically."""
        bbox = (100, 100, 200, 200)
        point = (150, 250)
        dist = TopologyEngine._dist_to_bbox(point, bbox)
        assert abs(dist - 50.0) < 1e-6

    def test_dist_to_bbox_corner(self):
        """Point at corner."""
        bbox = (100, 100, 200, 200)
        point = (250, 250)
        dist = TopologyEngine._dist_to_bbox(point, bbox)
        expected = math.sqrt(50**2 + 50**2)
        assert abs(dist - expected) < 1e-6

    def test_dist_to_bbox_on_edge(self):
        """Point on edge of bbox."""
        bbox = (100, 100, 200, 200)
        point = (100, 150)
        assert TopologyEngine._dist_to_bbox(point, bbox) == 0.0

    def test_infer_connectivity_simple(self):
        """Two symbols connected by a line should produce an edge."""
        symbols = [
            {"id": "A", "bbox": (50, 100, 80, 130)},
            {"id": "B", "bbox": (200, 100, 230, 130)},
        ]
        lines = [
            ((80, 115), (200, 115)),  # horizontal line connecting A and B
        ]
        edges = TopologyEngine.infer_connectivity(symbols, lines)
        assert len(edges) >= 1
        assert ("A", "B") in edges or ("B", "A") in edges

    def test_infer_connectivity_no_line(self):
        """Two symbols with no connecting line should produce no edges."""
        symbols = [
            {"id": "A", "bbox": (50, 100, 80, 130)},
            {"id": "B", "bbox": (200, 100, 230, 130)},
        ]
        lines = [
            ((500, 500), (600, 600)),  # line far away
        ]
        edges = TopologyEngine.infer_connectivity(symbols, lines)
        assert len(edges) == 0

    def test_infer_connectivity_empty(self):
        """No symbols or lines should produce no edges."""
        edges = TopologyEngine.infer_connectivity([], [])
        assert edges == []

    def test_infer_connectivity_three_symbols(self):
        """Three symbols in a chain: A-B-C should produce edges A-B and B-C."""
        symbols = [
            {"id": "A", "bbox": (50, 100, 80, 130)},
            {"id": "B", "bbox": (200, 100, 230, 130)},
            {"id": "C", "bbox": (350, 100, 380, 130)},
        ]
        lines = [
            ((80, 115), (200, 115)),   # A to B
            ((230, 115), (350, 115)),  # B to C
        ]
        edges = TopologyEngine.infer_connectivity(symbols, lines)
        edge_set = set(tuple(sorted(e)) for e in edges)
        assert ("A", "B") in edge_set
        assert ("B", "C") in edge_set

    def test_infer_connectivity_dedup(self):
        """Duplicate connections should be deduplicated."""
        symbols = [
            {"id": "A", "bbox": (50, 100, 80, 130)},
            {"id": "B", "bbox": (200, 100, 230, 130)},
        ]
        lines = [
            ((80, 115), (200, 115)),
            ((80, 116), (200, 116)),  # very close duplicate line
        ]
        edges = TopologyEngine.infer_connectivity(symbols, lines)
        edge_set = set(tuple(sorted(e)) for e in edges)
        assert len(edge_set) == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
