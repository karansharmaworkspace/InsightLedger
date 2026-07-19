"""
P&ID Digitization Pipeline
Orchestrates YOLO+SAHI detection + topology extraction + knowledge graph building.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.services.pid_detector import PIDDetector
from app.services.pid_ocr import TrocrPIDOCR
from app.services.topology_engine import TopologyEngine
from app.services.entity_extraction import EntityExtractor
from app.services.knowledge_graph import KnowledgeGraphService


class PIDDigitizer:
    """Full P&ID digitization pipeline."""

    def __init__(self, storage_dir: str = "storage", model_path: str = "models/32classes.pt"):
        self.storage_dir = Path(storage_dir)
        self.detector = PIDDetector(model_path=model_path)
        self.ocr = TrocrPIDOCR(gpu=False)
        self.entity_extractor = EntityExtractor()
        self.kg_service = KnowledgeGraphService(storage_dir)

    def digitize(self, image_path: str) -> Dict[str, Any]:
        """
        Run full P&ID digitization pipeline.

        Returns:
            {
                "symbols": [...],       # Detected equipment/instruments with tags
                "lines": [...],         # Detected lines with ISA-5.1 classification
                "connections": [...],   # Equipment-to-equipment connections
                "instrument_loops": {...},  # Instrument loop groupings
                "knowledge_graph": {...}  # Graph for visualization
            }
        """
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")

        # Step 1: YOLO + SAHI detection for symbols
        print("[1/4] Running YOLO + SAHI symbol detection...")
        symbols = self.detector.detect_with_labels(image_path)
        print(f"  Detected {len(symbols)} symbols")

        # Step 2: OCR for additional text labels (tags, parameters, notes)
        print("[2/4] Running OCR for text labels...")
        ocr_results = self.ocr.run(img, conf_thresh=0.2, prefer_tags=True)
        print(f"  Found {len(ocr_results)} text regions")

        # Merge OCR labels into symbols that don't have labels
        symbols = self._merge_ocr_labels(symbols, ocr_results)

        # Step 3: Detect and classify lines
        print("[3/4] Detecting topology (lines + classification)...")
        lines = TopologyEngine.find_lines(image_path, symbol_bboxes=[s["bbox"] for s in symbols])
        typed_lines = TopologyEngine.classify_lines(lines, image_path, symbols=symbols)
        print(f"  Found {len(typed_lines)} lines")

        # Step 4: Infer connectivity
        print("[4/4] Inferring connections...")
        connections = TopologyEngine.infer_connectivity(symbols, lines, threshold=350)
        typed_connections = TopologyEngine.enrich_edges_with_types(connections, typed_lines, symbols)

        # Group instrument loops
        instrument_loops = TopologyEngine.group_instrument_loops(symbols, typed_lines)

        # Build knowledge graph
        self._build_kg_from_pid(symbols, typed_connections)

        return {
            "symbols": symbols,
            "lines": self._format_lines(typed_lines),
            "connections": self._format_connections(typed_connections, symbols),
            "instrument_loops": instrument_loops,
            "knowledge_graph": self.kg_service.get_graph_data(),
        }

    def _merge_ocr_labels(self, symbols: List[Dict], ocr_results: List) -> List[Dict]:
        """Merge OCR text into symbols that lack labels."""
        for sym in symbols:
            if sym.get("label_confidence", 0) > 0:
                continue  # Already has label from direct detection match

            sym_cx = (sym["bbox"][0] + sym["bbox"][2]) / 2
            sym_cy = (sym["bbox"][1] + sym["bbox"][3]) / 2

            best_dist = 100
            for ocr_bbox, ocr_text, ocr_conf in ocr_results:
                ocr_cx = sum(p[0] for p in ocr_bbox) / len(ocr_bbox)
                ocr_cy = sum(p[1] for p in ocr_bbox) / len(ocr_bbox)

                dist = ((sym_cx - ocr_cx) ** 2 + (sym_cy - ocr_cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    sym["tag"] = ocr_text
                    sym["label_confidence"] = ocr_conf

        return symbols

    def _format_lines(self, typed_lines) -> List[Dict[str, Any]]:
        """Format typed lines for output."""
        result = []
        for p1, p2, line_type, subtype in typed_lines:
            result.append({
                "start": list(p1),
                "end": list(p2),
                "type": line_type,
                "subtype": subtype,
            })
        return result

    def _format_connections(self, typed_connections, symbols) -> List[Dict[str, Any]]:
        """Format connections with equipment tags."""
        sym_map = {s["id"]: s["tag"] for s in symbols}
        result = []
        for source_id, target_id, line_type, subtype in typed_connections:
            result.append({
                "source": sym_map.get(source_id, source_id),
                "target": sym_map.get(target_id, target_id),
                "line_type": line_type,
            })
        return result

    def _build_kg_from_pid(self, symbols, connections):
        """Add extracted equipment and connections to knowledge graph."""
        for sym in symbols:
            if sym["type"] in ("equipment", "instrument", "valve"):
                self.kg_service.add_node(
                    node_id=sym["tag"],
                    name=sym["tag"],
                    node_type=sym["type"],
                    properties={"bbox": sym["bbox"], "confidence": sym["confidence"]}
                )

        for source, target, line_type, _ in connections:
            if source in [s["tag"] for s in symbols] and target in [s["tag"] for s in symbols]:
                self.kg_service.add_edge(source, target, line_type)
