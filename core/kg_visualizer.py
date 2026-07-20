"""
Knowledge Graph Visualizer
Generates interactive HTML visualization of the knowledge graph.
"""
from dataclasses import dataclass
from typing import List, Dict, Any
import json
import os
import html as html_mod


@dataclass
class NodeStyle:
    color: str
    size: int
    shape: str


# Color scheme by entity type
ENTITY_COLORS = {
    "equipment_tag": "#3498db",  # Blue
    "personnel": "#2ecc71",      # Green
    "regulatory_ref": "#e74c3c", # Red
    "date": "#f39c12",           # Orange
    "parameter": "#9b59b6",      # Purple
    "work_order": "#1abc9c",     # Teal
    "failure_mode": "#e67e22",   # Dark Orange
    "location": "#34495e",       # Dark Gray
}


class KGVisualizer:
    def __init__(self):
        self.default_style = NodeStyle("#95a5a6", 25, "dot")

    def generate_graph_html(self, kg_data: Dict[str, Any], output_path: str) -> str:
        """
        Generate interactive HTML visualization of the knowledge graph.

        Args:
            kg_data: Knowledge graph data with 'nodes' and 'edges' dicts
                     (matches KnowledgeGraph.nodes and .edges format)
            output_path: Path to save HTML file

        Returns:
            Path to generated HTML file
        """
        # Normalize: accept both dict-of-dicts and dict-of-lists formats
        nodes = kg_data.get("nodes", {})
        edges = kg_data.get("edges", [])
        try:
            from pyvis.network import Network
        except ImportError:
            # Fallback: generate static HTML with D3.js
            return self._generate_d3_html(kg_data, output_path)

        net = Network(height="700px", width="100%", bgcolor="#1a1a2e", font_color="white")
        net.set_options("""
        {
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -3000,
              "centralGravity": 0.3,
              "springLength": 150,
              "springConstant": 0.02
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 100
          }
        }
        """)

        # Add nodes
        for node_id, node_data in kg_data.get("nodes", {}).items():
            entity_type = node_data.get("type", "unknown")
            color = ENTITY_COLORS.get(entity_type, self.default_style.color)
            label = node_data.get("value", node_id)
            sources = node_data.get("sources", [])
            confidence = node_data.get("confidence", 0)

            title = f"<b>{html_mod.escape(str(label))}</b><br>"
            title += f"Type: {html_mod.escape(entity_type)}<br>"
            title += f"Confidence: {confidence:.0%}<br>"
            title += f"Sources: {html_mod.escape(', '.join(sources))}"

            net.add_node(
                node_id,
                label=label,
                color=color,
                size=self.default_style.size,
                title=title,
                shape=self.default_style.shape,
            )

        # Add edges
        for edge in kg_data.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")
            relation = edge.get("relation", "related_to")

            if source in kg_data.get("nodes", {}) and target in kg_data.get("nodes", {}):
                net.add_edge(source, target, label=relation, color="#666666")

        # Save
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        net.save_graph(output_path)

        # Add custom styling
        self._add_custom_styles(output_path)

        return output_path

    def _generate_d3_html(self, kg_data: Dict[str, Any], output_path: str) -> str:
        """Fallback D3.js visualization when pyvis not available."""
        nodes = []
        for node_id, node_data in kg_data.get("nodes", {}).items():
            entity_type = node_data.get("type", "unknown")
            color = ENTITY_COLORS.get(entity_type, self.default_style.color)
            nodes.append({
                "id": node_id,
                "label": node_data.get("value", node_id),
                "color": color,
                "type": entity_type,
            })

        edges = []
        for edge in kg_data.get("edges", []):
            edges.append({
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation": edge.get("relation", "related_to"),
            })

        d3_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; background: #1a1a2e; }}
        svg {{ width: 100%; height: 700px; }}
        .node {{ cursor: pointer; }}
        .node circle {{ stroke: #fff; stroke-width: 1.5px; }}
        .node text {{ fill: white; font-size: 10px; pointer-events: none; }}
        .link {{ stroke: #666; stroke-opacity: 0.6; }}
        .link-label {{ fill: #888; font-size: 8px; }}
    </style>
</head>
<body>
<svg id="graph"></svg>
<script>
const data = {json.dumps({"nodes": nodes, "edges": edges})};

const svg = d3.select("#graph");
const width = svg.node().getBoundingClientRect().width;
const height = 700;

const simulation = d3.forceSimulation(data.nodes)
    .force("link", d3.forceLink(data.edges).id(d => d.id).distance(150))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2));

const link = svg.append("g")
    .selectAll("line")
    .data(data.edges)
    .join("line")
    .attr("class", "link");

const linkLabel = svg.append("g")
    .selectAll("text")
    .data(data.edges)
    .join("text")
    .attr("class", "link-label")
    .text(d => d.relation);

const node = svg.append("g")
    .selectAll("g")
    .data(data.nodes)
    .join("g")
    .attr("class", "node")
    .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

node.append("circle")
    .attr("r", 12)
    .attr("fill", d => d.color);

node.append("text")
    .attr("dx", 15)
    .attr("dy", 4)
    .text(d => d.label);

simulation.on("tick", () => {{
    link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    linkLabel.attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);
    node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});

function dragstarted(event) {{
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
}}

function dragged(event) {{
    event.subject.fx = event.x;
    event.subject.fy = event.y;
}}

function dragended(event) {{
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
}}
</script>
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(d3_html)

        return output_path

    def _add_custom_styles(self, html_path: str):
        """Add custom styling to pyvis-generated HTML."""
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Add legend CSS
            legend_style = """
            <style>
                #legend {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(26, 26, 46, 0.9);
                    padding: 10px;
                    border-radius: 5px;
                    color: white;
                    font-size: 12px;
                }
                .legend-item {
                    display: flex;
                    align-items: center;
                    margin: 5px 0;
                }
                .legend-color {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
            </style>
            """

            legend_html = """
            <div id="legend">
                <b>Entity Types</b>
                <div class="legend-item"><div class="legend-color" style="background: #3498db;"></div>Equipment</div>
                <div class="legend-item"><div class="legend-color" style="background: #2ecc71;"></div>Personnel</div>
                <div class="legend-item"><div class="legend-color" style="background: #e74c3c;"></div>Regulation</div>
                <div class="legend-item"><div class="legend-color" style="background: #f39c12;"></div>Date</div>
                <div class="legend-item"><div class="legend-color" style="background: #9b59b6;"></div>Parameter</div>
                <div class="legend-item"><div class="legend-color" style="background: #1abc9c;"></div>Work Order</div>
            </div>
            """

            # Insert styles and legend
            content = content.replace("<head>", f"<head>{legend_style}")
            content = content.replace("<body>", f"<body>{legend_html}")

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"[KGVisualizer] Style injection failed: {e}")


if __name__ == "__main__":
    # Demo
    from core.knowledge_graph import KnowledgeGraph
    import tempfile

    kg = KnowledgeGraph(os.path.join(tempfile.mkdtemp(), "test_kg.json"))

    # Add sample entities
    kg.add_entity("equipment_tag", "V-101", "demo", confidence=0.95)
    kg.add_entity("equipment_tag", "P-202A", "demo", confidence=0.90)
    kg.add_entity("personnel", "John Smith", "demo", confidence=0.85)
    kg.add_entity("regulatory_ref", "API 570", "demo", confidence=0.99)
    kg.add_entity("date", "2026-01-15", "demo", confidence=0.95)

    # Add relationships
    kg.add_edge("V-101", "P-202A", "connected_to")
    kg.add_edge("V-101", "John Smith", "maintained_by")
    kg.add_edge("V-101", "API 570", "regulated_by")
    kg.add_edge("P-202A", "API 570", "regulated_by")

    # Generate visualization
    visualizer = KGVisualizer()
    output = visualizer.generate_graph_html({"nodes": kg.nodes, "edges": kg.edges}, "knowledge_graph.html")
    print(f"Generated: {output}")
