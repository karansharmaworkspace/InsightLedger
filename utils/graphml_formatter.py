"""
GraphML export formatter for P&ID digitization pipeline.

Produces GraphML XML (yEd/Gephi-compatible) from the same node/edge data
that feeds DEXPI JSON output. Uses stdlib xml.etree.ElementTree — zero
extra dependencies.
"""

import json
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from collections import Counter

GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"
YED_NS = "http://www.yworks.com/xml/graphml"
XLINK_NS = "http://www.w3.org/1999/xlink"

# ---------------------------------------------------------------------------
# key-id registry — each <key> gets a stable d0…dN id shared across the file
# ---------------------------------------------------------------------------
_NODE_KEYS = [
    ("label",      "string", "Display label / coarse type"),
    ("Labels",     "string", "OCR-extracted text"),
    ("raw_id",     "int",    "YOLO class ID"),
    ("fine_class", "string", "Reclassified fine-grained type"),
    ("fine_raw_id","string", "Reclassification raw identifier"),
    ("type_key",   "string", "Coarse type key from class mapping"),
    ("xmin",       "double", "Bounding-box left"),
    ("ymin",       "double", "Bounding-box top"),
    ("xmax",       "double", "Bounding-box right"),
    ("ymax",       "double", "Bounding-box bottom"),
]

_EDGE_KEYS = [
    ("edge_label", "string", "Connection type (solid, dashed, etc.)"),
]

# yEd shape-node key (single shared data slot for node graphics)
_YED_NODE_GRAPHICS_KEY = "nodeGraphics"
_YED_EDGE_GRAPHICS_KEY = "edgeGraphics"


class GraphMLFormatter:
    """Convert DEXPI-structured node/edge dicts into GraphML XML."""

    @staticmethod
    def _sanitize_id(raw: str) -> str:
        """Produce a valid XML NCName from an arbitrary string."""
        if not raw:
            return "_"
        safe = "".join(c if c.isalnum() or c in "_-." else "_" for c in raw)
        if not safe or safe[0].isdigit() or safe[0] == ".":
            safe = "_" + safe
        return safe

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def build_xml(nodes: list, edges: list, visual: bool = True) -> ET.ElementTree:
        """Build an xml.etree.ElementTree from DEXPI-shaped data.

        Parameters
        ----------
        nodes : list[dict]
            Each dict has keys ``id``, ``type_key``, ``attrs``.
        edges : list[dict]
            Each dict has keys ``source``, ``target``, ``attrs``.
        visual : bool
            If True (default), include yEd graphics keys (d11/d12) for
            visualization tools. If False, emit a plain graph suitable
            for LLM consumption.

        Returns
        -------
        xml.etree.ElementTree
        """
        root = ET.Element(f"{{{GRAPHML_NS}}}graphml")
        ET.register_namespace("", GRAPHML_NS)
        ET.register_namespace("y", YED_NS)
        ET.register_namespace("xlink", XLINK_NS)

        # -- key declarations -----------------------------------------------
        key_map = {}  # logical name -> id string (e.g. "d0")

        for idx, (name, typ, desc) in enumerate(_NODE_KEYS):
            kid = f"d{idx}"
            key_map[f"node:{name}"] = kid
            key = ET.SubElement(root, f"{{{GRAPHML_NS}}}key")
            key.set("id", kid)
            key.set("for", "node")
            key.set("attr.name", name)
            key.set("attr.type", typ)

        offset = len(_NODE_KEYS)
        for idx, (name, typ, desc) in enumerate(_EDGE_KEYS):
            kid = f"d{offset + idx}"
            key_map[f"edge:{name}"] = kid
            key = ET.SubElement(root, f"{{{GRAPHML_NS}}}key")
            key.set("id", kid)
            key.set("for", "edge")
            key.set("attr.name", name)
            key.set("attr.type", typ)

        # yEd graphics keys — only when visual=True
        if visual:
            yed_node_kid = f"d{offset + len(_EDGE_KEYS)}"
            key_map[_YED_NODE_GRAPHICS_KEY] = yed_node_kid
            yed_node_key = ET.SubElement(root, f"{{{GRAPHML_NS}}}key")
            yed_node_key.set("id", yed_node_kid)
            yed_node_key.set("for", "node")
            yed_node_key.set("yfiles.type", "nodegraphics")
            yed_node_key.set("attr.name", "nodegraphics")

            yed_edge_kid = f"d{offset + len(_EDGE_KEYS) + 1}"
            key_map[_YED_EDGE_GRAPHICS_KEY] = yed_edge_kid
            yed_edge_key = ET.SubElement(root, f"{{{GRAPHML_NS}}}key")
            yed_edge_key.set("id", yed_edge_kid)
            yed_edge_key.set("for", "edge")
            yed_edge_key.set("yfiles.type", "edgegraphics")
            yed_edge_key.set("attr.name", "edgegraphics")

        # -- <graph> container ----------------------------------------------
        graph = ET.SubElement(root, f"{{{GRAPHML_NS}}}graph")
        graph.set("id", "G")
        graph.set("edgedefault", "undirected")

        # -- nodes ----------------------------------------------------------
        for node in nodes:
            node_id = GraphMLFormatter._sanitize_id(node.get("id", ""))
            nd = ET.SubElement(graph, f"{{{GRAPHML_NS}}}node")
            nd.set("id", node_id)

            attrs = node.get("attrs", {})

            # Data elements for each known key
            for name, _typ, _desc in _NODE_KEYS:
                kid = key_map.get(f"node:{name}")
                val = attrs.get(name, "")
                if val == "" or val is None:
                    continue
                data = ET.SubElement(nd, f"{{{GRAPHML_NS}}}data")
                data.set("key", kid)
                data.text = str(val)

            # Type_key stored as node-level data too
            type_key_kid = key_map.get("node:type_key")
            if type_key_kid:
                tk = node.get("type_key", "")
                if tk:
                    data = ET.SubElement(nd, f"{{{GRAPHML_NS}}}data")
                    data.set("key", type_key_kid)
                    data.text = tk

            # yEd shape-node graphics (preserve bounding-box positions)
            if visual:
                GraphMLFormatter._attach_yed_node_graphics(
                    nd, key_map[_YED_NODE_GRAPHICS_KEY], node_id, attrs
                )

        # -- edges ----------------------------------------------------------
        for idx, edge in enumerate(edges):
            src = GraphMLFormatter._sanitize_id(edge.get("source", ""))
            tgt = GraphMLFormatter._sanitize_id(edge.get("target", ""))
            if not src or not tgt:
                continue

            ed = ET.SubElement(graph, f"{{{GRAPHML_NS}}}edge")
            ed.set("id", f"e{idx}")
            ed.set("source", src)
            ed.set("target", tgt)

            eattrs = edge.get("attrs", {})
            for name, _typ, _desc in _EDGE_KEYS:
                kid = key_map.get(f"edge:{name}")
                val = eattrs.get(name, "")
                if val == "" or val is None:
                    continue
                data = ET.SubElement(ed, f"{{{GRAPHML_NS}}}data")
                data.set("key", kid)
                data.text = str(val)

            # yEd edge graphics
            if visual:
                GraphMLFormatter._attach_yed_edge_graphics(
                    ed, key_map[_YED_EDGE_GRAPHICS_KEY], eattrs
                )

        return ET.ElementTree(root)

    @staticmethod
    def to_string(nodes: list, edges: list, visual: bool = True) -> str:
        """Return pretty-printed GraphML XML string."""
        tree = GraphMLFormatter.build_xml(nodes, edges, visual=visual)
        raw = ET.tostring(tree.getroot(), encoding="unicode", xml_declaration=False)
        dom = minidom.parseString(raw)
        return dom.toprettyxml(indent="  ")

    @staticmethod
    def export(nodes: list, edges: list, path: str, visual: bool = True) -> None:
        """Write GraphML to *path*.

        Raises ``FileNotFoundError`` if the parent directory does not exist.
        """
        xml_str = GraphMLFormatter.to_string(nodes, edges, visual=visual)
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_str)

    @staticmethod
    def stats(nodes: list, edges: list) -> dict:
        """Return summary statistics for the graph."""
        type_counts = Counter(n.get("type_key", "unknown") for n in nodes)
        edge_labels = Counter(e.get("attrs", {}).get("edge_label", "unknown") for e in edges)
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "nodes_by_type": dict(type_counts.most_common()),
            "edges_by_label": dict(edge_labels.most_common()),
        }

    @staticmethod
    def export_stats(nodes: list, edges: list, path: str) -> None:
        """Write graph statistics as JSON to *path*."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(GraphMLFormatter.stats(nodes, edges), f, indent=2)

    # ------------------------------------------------------------------
    # yEd graphics helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _attach_yed_node_graphics(
        parent: ET.Element, key_id: str, node_id: str, attrs: dict
    ) -> None:
        """Embed a ``<y:ShapeNode>`` so yEd shows the shape at the right place."""
        x = float(attrs.get("xmin", 0))
        y = float(attrs.get("ymin", 0))
        w = float(attrs.get("xmax", 0)) - x
        h = float(attrs.get("ymax", 0)) - y
        if w <= 0:
            w = 40
        if h <= 0:
            h = 40

        # Map common P&ID types to yEd shapes for visual fidelity
        label = str(attrs.get("label", ""))
        shape_type = "rectangle"  # default
        if any(kw in label.lower() for kw in ("valve", "gate")):
            shape_type = "diamond"
        elif any(kw in label.lower() for kw in ("vessel", "tank", "column")):
            shape_type = "ellipse"
        elif any(kw in label.lower() for kw in ("pump", "motor", "compressor")):
            shape_type = "roundrectangle"
        elif any(kw in label.lower() for kw in ("instrument", "indicator", "controller")):
            shape_type = "hexagon"

        data = ET.SubElement(parent, f"{{{GRAPHML_NS}}}data")
        data.set("key", key_id)

        shape_node = ET.SubElement(data, f"{{{YED_NS}}}ShapeNode")
        geo = ET.SubElement(shape_node, f"{{{YED_NS}}}Geometry")
        geo.set("x", f"{x:.1f}")
        geo.set("y", f"{y:.1f}")
        geo.set("width", f"{w:.1f}")
        geo.set("height", f"{h:.1f}")

        fill = ET.SubElement(shape_node, f"{{{YED_NS}}}Fill")
        fill.set("color", "#99CCFF")
        fill.set("transparent", "false")

        border = ET.SubElement(shape_node, f"{{{YED_NS}}}BorderStyle")
        border.set("color", "#000000")
        border.set("type", "line")
        border.set("width", "1.0")

        shape = ET.SubElement(shape_node, f"{{{YED_NS}}}Shape")
        shape.set("type", shape_type)

        nl = ET.SubElement(shape_node, f"{{{YED_NS}}}NodeLabel")
        nl.set("alignment", "center")
        nl.set("autoSizePolicy", "content")
        nl.set("fontSize", "10")
        nl.set("fontFamily", "Dialog")
        nl.text = node_id

    @staticmethod
    def _attach_yed_edge_graphics(
        parent: ET.Element, key_id: str, attrs: dict
    ) -> None:
        """Embed a ``<y:PolyLineEdge>`` for yEd edge rendering."""
        data = ET.SubElement(parent, f"{{{GRAPHML_NS}}}data")
        data.set("key", key_id)

        ple = ET.SubElement(data, f"{{{YED_NS}}}PolyLineEdge")
        arrows = ET.SubElement(ple, f"{{{YED_NS}}}Arrows")
        arrows.set("source", "none")
        arrows.set("target", "standard")

        ls = ET.SubElement(ple, f"{{{YED_NS}}}LineStyle")
        ls.set("color", "#000000")
        ls.set("type", "line")
        ls.set("width", "1.0")

        label_text = str(attrs.get("edge_label", ""))
        if label_text and label_text != "solid":
            el = ET.SubElement(ple, f"{{{YED_NS}}}EdgeLabel")
            el.set("alignment", "center")
            el.set("fontSize", "9")
            el.text = label_text
