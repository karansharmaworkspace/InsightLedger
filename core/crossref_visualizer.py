"""
Cross-Reference Visualizer
Shows which documents reference the same equipment/standards.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Set
import html as html_mod
import os
from collections import defaultdict


@dataclass
class CrossRefMatrix:
    documents: List[str]
    entities: List[str]
    matrix: List[List[bool]]
    entity_types: Dict[str, str]


class CrossRefVisualizer:
    def __init__(self):
        pass

    def build_matrix(self, chunks: List[Dict[str, Any]], extractor=None) -> CrossRefMatrix:
        """
        Build cross-reference matrix from document chunks.

        Args:
            chunks: List of document chunks with 'source' and 'content'
            extractor: Optional EntityExtractor instance

        Returns:
            CrossRefMatrix with documents x entities mapping
        """
        if extractor is None:
            from core.entity_extractor import EntityExtractor
            extractor = EntityExtractor()

        doc_entities: Dict[str, Set[str]] = defaultdict(set)
        entity_types: Dict[str, str] = {}

        for chunk in chunks:
            source = chunk.get("source", "unknown")
            content = chunk.get("content", "")

            entities = extractor.extract(content)
            for entity in entities:
                doc_entities[source].add(entity.value)
                entity_types[entity.value] = entity.entity_type

        # Get unique documents and entities
        documents = sorted(doc_entities.keys())
        all_entities = set()
        for ents in doc_entities.values():
            all_entities.update(ents)
        entities = sorted(all_entities)

        # Build matrix
        matrix = []
        for doc in documents:
            row = [ent in doc_entities[doc] for ent in entities]
            matrix.append(row)

        return CrossRefMatrix(
            documents=documents,
            entities=entities,
            matrix=matrix,
            entity_types=entity_types,
        )

    def generate_html(self, matrix: CrossRefMatrix, output_path: str) -> str:
        """
        Generate interactive HTML cross-reference table.

        Args:
            matrix: CrossRefMatrix data
            output_path: Path to save HTML file

        Returns:
            Path to generated HTML file
        """
        # Color scheme by entity type
        type_colors = {
            "equipment_tag": "#3498db",
            "personnel": "#2ecc71",
            "regulatory_ref": "#e74c3c",
            "date": "#f39c12",
            "parameter": "#9b59b6",
            "work_order": "#1abc9c",
        }

        # Build table rows
        rows_html = ""
        for i, doc in enumerate(matrix.documents):
            doc_name = os.path.basename(doc)
            rows_html += f'<tr><td class="doc-name">{doc_name}</td>'
            for j, ent in enumerate(matrix.entities):
                if matrix.matrix[i][j]:
                    ent_type = matrix.entity_types.get(ent, "unknown")
                    color = type_colors.get(ent_type, "#95a5a6")
                    rows_html += f'<td class="entity-cell" style="background: {color};" title="{html_mod.escape(ent)} ({html_mod.escape(ent_type)})"></td>'
                else:
                    rows_html += '<td class="empty-cell"></td>'
            rows_html += '</tr>\n'

        # Entity headers
        entity_headers = ""
        for ent in matrix.entities:
            ent_type = matrix.entity_types.get(ent, "unknown")
            color = type_colors.get(ent_type, "#95a5a6")
            entity_headers += f'<th class="entity-header" style="background: {color};">{html_mod.escape(ent)}</th>\n'

        # Document count per entity
        entity_counts = []
        for j in range(len(matrix.entities)):
            count = sum(1 for i in range(len(matrix.documents)) if matrix.matrix[i][j])
            entity_counts.append(count)

        # Find shared entities (referenced by 2+ documents)
        shared = [(matrix.entities[j], entity_counts[j])
                  for j in range(len(matrix.entities)) if entity_counts[j] >= 2]

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Cross-Reference Matrix</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
        h1 {{ color: #fff; margin-bottom: 10px; }}
        .subtitle {{ color: #888; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-box {{ background: #16213e; padding: 15px; border-radius: 8px; border: 1px solid #333; }}
        .stat-value {{ font-size: 24px; color: #0078d4; font-weight: bold; }}
        .stat-label {{ color: #888; font-size: 12px; }}
        .table-container {{ overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ padding: 8px; text-align: center; border: 1px solid #333; }}
        .doc-name {{ text-align: left; color: #fff; font-weight: 500; white-space: nowrap; }}
        .entity-header {{ writing-mode: vertical-rl; text-orientation: mixed; color: #fff; font-size: 11px; max-width: 30px; }}
        .entity-cell {{ min-width: 30px; cursor: pointer; }}
        .entity-cell:hover {{ opacity: 0.8; outline: 2px solid #fff; }}
        .empty-cell {{ background: #0f0f23; }}
        .legend {{ margin-top: 20px; display: flex; gap: 15px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 3px; }}
        .shared-section {{ margin-top: 20px; background: #16213e; padding: 15px; border-radius: 8px; }}
        .shared-section h2 {{ color: #fff; margin-bottom: 10px; font-size: 16px; }}
        .shared-item {{ display: inline-block; background: #0f3460; padding: 5px 10px; margin: 3px; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Cross-Reference Matrix</h1>
    <p class="subtitle">Documents sharing equipment, standards, and entities</p>

    <div class="stats">
        <div class="stat-box">
            <div class="stat-value">{len(matrix.documents)}</div>
            <div class="stat-label">Documents</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{len(matrix.entities)}</div>
            <div class="stat-label">Unique Entities</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{len(shared)}</div>
            <div class="stat-label">Shared Entities</div>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Document</th>
                    {entity_headers}
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>

    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: #3498db;"></div>Equipment</div>
        <div class="legend-item"><div class="legend-color" style="background: #2ecc71;"></div>Personnel</div>
        <div class="legend-item"><div class="legend-color" style="background: #e74c3c;"></div>Regulation</div>
        <div class="legend-item"><div class="legend-color" style="background: #f39c12;"></div>Date</div>
        <div class="legend-item"><div class="legend-color" style="background: #9b59b6;"></div>Parameter</div>
    </div>

    {"<div class='shared-section'><h2>Shared Entities (referenced by 2+ documents)</h2>" + "".join(f'<span class="shared-item">{html_mod.escape(ent)} ({count} docs)</span>' for ent, count in shared) + "</div>" if shared else ""}
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path


if __name__ == "__main__":
    # Demo
    from core.entity_extractor import EntityExtractor

    extractor = EntityExtractor()

    # Sample chunks from different documents
    chunks = [
        {
            "source": "maintenance_report.txt",
            "content": "V-101 inspected on 2026-01-15 per API 570. Technician: John Smith.",
        },
        {
            "source": "safety_manual.txt",
            "content": "V-101 must be inspected every 6 months per API 570. OSHA 1910.119 applies.",
        },
        {
            "source": "inspection_log.txt",
            "content": "V-101 inspection completed by John Smith. Next due: 2026-07-15.",
        },
    ]

    viz = CrossRefVisualizer()
    matrix = viz.build_matrix(chunks, extractor)
    output = viz.generate_html(matrix, "crossref_matrix.html")
    print(f"Generated: {output}")
    print(f"Documents: {len(matrix.documents)}")
    print(f"Entities: {len(matrix.entities)}")
