import os
import json
import time
import threading
import cv2
import numpy as np
from ensemble_boxes import weighted_boxes_fusion

from utils.topology_engine import TopologyEngine
from utils.formatter import DexpiFormatter
from utils.graphml_formatter import GraphMLFormatter
from core.class_memory import ClassMemory
from core.visual_rag import VisualRAG
from utils.translations import tr_class
from core.pid_ocr import TrocrPIDOCR

class UniversalEngine:
    def __init__(self, model_path="models/32class.pt", output_dir="output", lang="en", sahi_tile_size=640):
        self.model_path = model_path
        self.output_dir = output_dir
        self.lang = lang
        os.makedirs(output_dir, exist_ok=True)
        
        from ultralytics import YOLO
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                f"Download the model or set PT_MODEL_PATH in .env"
            )
        self.model_coarse = YOLO(model_path)
        
        # Load real class names from mapping file (model.names has generic Class_1, Class_2...)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        mapping_path = os.path.join(base_dir, 'models', 'class_mapping.json')
        if os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                raw_map = json.load(f)
            self._class_names = {int(k): v for k, v in raw_map.items()}
        else:
            self._class_names = self.model_coarse.names
        self.class_memory = ClassMemory(
            memory_path=os.path.join(base_dir, 'models', 'class_memory.json'),
            gallery_dir=os.path.join(base_dir, 'assets', 'class_gallery')
        )
        self.rag = VisualRAG(
            gallery_dir=os.path.join(base_dir, 'assets', 'class_gallery'),
            cache_path=os.path.join(base_dir, 'models', 'dinov2_embeddings.npz')
        ).load()

        self.sahi_available = False
        self.sahi_tile_size = sahi_tile_size
        self.sahi_params = {}
        self.detection_model = None
        self._ocr = None  # lazy init
        self._init_sahi()

    def _init_sahi(self):
        """Attempt to initialize SAHI tiled inference."""
        self.sahi_available = False
        try:
            from sahi import AutoDetectionModel
            from sahi.predict import get_sliced_prediction
            self.sahi_available = True
            self.detection_model = AutoDetectionModel.from_pretrained(
                model_type='ultralytics',
                model_path=self.model_path,
                confidence_threshold=0.05,
                image_size=self.sahi_tile_size,
            )
            self.sahi_params = {
                'slice_height': self.sahi_tile_size,
                'slice_width': self.sahi_tile_size,
                'overlap_height_ratio': 0.2,
                'overlap_width_ratio': 0.2,
            }
            print(f"[ENGINE] SAHI initialized with {self.sahi_tile_size}px tiles")
        except ImportError:
            print("[ENGINE] SAHI not available — will use direct YOLO inference")

    def set_language(self, lang):
        if lang == self.lang:
            return
        self.lang = lang

    def _get_workspace_roi(self, w, h, img):
        return (0, 0, w, h)

    def _preprocess_image(self, img):
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        normalized = clahe.apply(gray)
        
        contours, _ = cv2.findContours(normalized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_pts = np.vstack(contours) if contours else np.array([])
        if len(all_pts) > 0:
            rect = cv2.minAreaRect(all_pts)
            angle = rect[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            if abs(angle) > 0.5:
                (h, w) = normalized.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                deskewed = cv2.warpAffine(normalized, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            else:
                deskewed = normalized
        else:
            deskewed = normalized
        
        result = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
        return result

    def process(self, image_path, callback=None, logger=None, lang=None, 
                on_line_found=None, on_edge_found=None, on_symbol_classified=None,
                on_node_found=None, on_ocr_bbox=None):
        """Run the full digitization pipeline.
        
        Real-time callbacks:
            on_line_found(p1, p2, line_type) - called for each pipeline segment detected
            on_edge_found(src_id, tgt_id, line_type) - called for each connection inferred
            on_symbol_classified(node_id, class_name) - called when symbol classification completes
            on_node_found(node_id, bbox) - called when a symbol node is validated
            on_ocr_bbox(x1, y1, x2, y2, text, conf) - called for each OCR text region detected
        
        Returns dict with keys:
            'json' — DEXPI output
            'detections' — raw detection list
            'lines' — topology line segments for GUI overlay
            'edges' — connectivity edges
            'graphml' — GraphML XML string
        """
        if lang and lang != self.lang:
            self.set_language(lang)
        
        def log(msg):
            if logger: logger(f'[ENGINE] {msg}')
        
        log(f'Initializing digitization for {os.path.basename(image_path)}')
        start_time = time.time()
        
        full_img = cv2.imread(image_path)
        if full_img is None: return {'json': {}, 'detections': [], 'lines': [], 'edges': [], 'graphml': ''}
        
        # ponytail: Run OCR on cropped image BEFORE preprocessing (CLAHE + deskew)
        # Preprocessing changes coordinate space, causing shifted overlays
        log("Starting OCR thread (parallel with SAHI scan)...")
        ocr_thread, ocr_result = self._start_ocr_thread(full_img)
        
        full_img = self._preprocess_image(full_img)
        
        h_img, w_img = full_img.shape[:2]
        rx, ry, rw, rh = self._get_workspace_roi(w_img, h_img, full_img)
        roi_x1, roi_y1, roi_x2, roi_y2 = rx, ry, rx + rw, ry + rh
        log(f'Workspace: {roi_x1},{roi_y1} to {roi_x2},{roi_y2}')
        
        detections = self._run_coarse_scan(image_path, callback=callback, logger=logger)
        log(f'Coarse scan complete. Found {len(detections)} candidates.')
        
        validated_nodes = []
        for i, det in enumerate(detections):
            bbox = det['bbox']
            x1, y1, x2, y2 = bbox
            if x1 < roi_x1 or y1 < roi_y1 or x2 > roi_x2 or y2 > roi_y2: continue
            
            if self._is_plausible_symbol(bbox, h_img):
                coarse_name = self._map_class(det['class'])
                display_name = tr_class(coarse_name, self.lang)
                node_id = f'{coarse_name}_{i}'
                validated_nodes.append({
                    'id': node_id,
                    'type': display_name,
                    'type_key': coarse_name,
                    'raw_id': det['class'],
                    'coordinates': bbox
                })
                if on_node_found:
                    on_node_found(node_id, bbox)

        log("Waiting for OCR thread to finish...")
        ocr_thread.join(timeout=300)
        
        if ocr_result['error']:
            log(f"OCR thread failed: {ocr_result['error']}")
        elif ocr_result['ocr_results'] is None:
            log('[OCR] No text detections found in image')
        else:
            ocr_results = ocr_result['ocr_results']
            log(f'[OCR] Detected {len(ocr_results)} text regions')
            
            for node in validated_nodes:
                x1, y1, x2, y2 = node['coordinates']
                bw, bh = x2 - x1, y2 - y1
                pad_x, pad_y = bw * 0.5, bh * 0.5
                ex1, ey1 = x1 - pad_x, y1 - pad_y
                ex2, ey2 = x2 + pad_x, y2 + pad_y
                inside = []
                for box, text, conf in ocr_results:
                    ocr_xs = [p[0] for p in box]
                    ocr_ys = [p[1] for p in box]
                    ocx = sum(ocr_xs) / len(ocr_xs)
                    ocy = sum(ocr_ys) / len(ocr_ys)
                    if ex1 <= ocx <= ex2 and ey1 <= ocy <= ey2:
                        inside.append((text, conf, ocy))
                if inside:
                    inside.sort(key=lambda t: t[2])
                    node['Labels'] = ' '.join(t[0] for t in inside)
                    node['ocr_confidence'] = max(t[1] for t in inside)
                    node['ocr_all'] = [t[0] for t in inside]
            matched = sum(1 for n in validated_nodes if 'Labels' in n)
            log(f'[OCR] {matched}/{len(validated_nodes)} symbols labeled')
            
            validated_nodes = self._merge_tag_segments(validated_nodes, log)
            
            if on_ocr_bbox:
                for box, text, conf in ocr_results:
                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]
                    on_ocr_bbox(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)), text, conf)

        log("Tracer: Generating pipeline skeleton...")
        symbol_bboxes = [n['coordinates'] for n in validated_nodes]
        lines = TopologyEngine.find_lines(image_path, symbol_bboxes=symbol_bboxes)
        log(f'Skeletonization complete. Traced {len(lines)} pipeline segments.')
        
        log("Classifying line types (process/signal/utility)...")
        typed_lines = TopologyEngine.classify_lines(lines, image_path)
        
        if on_line_found:
            for p1, p2, line_type, subtype in typed_lines:
                on_line_found(p1, p2, line_type)
        
        process_cnt = sum(1 for _, _, t, _ in typed_lines if t == "process")
        signal_cnt = sum(1 for _, _, t, _ in typed_lines if t == "signal")
        utility_cnt = sum(1 for _, _, t, _ in typed_lines if t == "utility")
        log(f"Line types: {process_cnt} process, {signal_cnt} signal, {utility_cnt} utility")
        
        log("Classifying symbols...")
        for node in validated_nodes:
            fine_class = self.classify_symbol(node, full_img)
            node['type'] = fine_class
            node['fine_class'] = fine_class
            # Emit symbol classification in real-time
            if on_symbol_classified:
                on_symbol_classified(node['id'], fine_class)
        log(f"Classification complete.")
        
        log(f'Topology Solver: Inferring connectivity for {len(validated_nodes)} symbols...')
        topo_symbols = [{'id': n['id'], 'bbox': n['coordinates']} for n in validated_nodes]
        edges = TopologyEngine.infer_connectivity(topo_symbols, lines)
        log(f'Connectivity graph solved. Identified {len(edges)} pipeline connections.')
        
        log("Enriching edges with line types...")
        typed_edges = TopologyEngine.enrich_edges_with_types(edges, typed_lines, topo_symbols)
        
        # Emit each edge in real-time
        if on_edge_found:
            for src_id, tgt_id, line_type, subtype in typed_edges:
                on_edge_found(src_id, tgt_id, line_type)
        
        log("Grouping instrument loops...")
        loops = TopologyEngine.group_instrument_loops(validated_nodes, typed_lines, full_img.shape)
        if loops:
            log(f"Found {len(loops)} instrument loops: {', '.join(f'{k}({len(v)})' for k, v in loops.items())}")
        else:
            log("No instrument loops detected.")
        
        final_json = DexpiFormatter.to_user_schema(validated_nodes, edges=typed_edges)
        base_name = os.path.basename(image_path)
        out_path = os.path.join(self.output_dir, base_name + "_DIGITIZED.json")
        
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=2)

        graphml_path = os.path.join(self.output_dir, base_name + "_DIGITIZED.graphml")
        graphml_plain_path = os.path.join(self.output_dir, base_name + "_DIGITIZED_plain.graphml")
        stats_path = os.path.join(self.output_dir, base_name + "_STATS.json")
        try:
            GraphMLFormatter.export(final_json['nodes'], final_json['edges'], graphml_path, visual=True)
            log(f'GraphML export written to {graphml_path}')
            GraphMLFormatter.export(final_json['nodes'], final_json['edges'], graphml_plain_path, visual=False)
            log(f'Plain GraphML export written to {graphml_plain_path}')
            GraphMLFormatter.export_stats(final_json['nodes'], final_json['edges'], stats_path)
            log(f'Graph stats written to {stats_path}')
        except Exception as e:
            log(f'GraphML export failed: {e}')
            
        viz_path = os.path.join(self.output_dir, base_name + "_BOXED.jpg")
        self._save_visualization(image_path, validated_nodes, viz_path, edges=typed_edges)
        log(f'Digitization Success. Runtime: {time.time()-start_time:.2f}s')
        
        return {
            'json': final_json,
            'detections': validated_nodes,
            'lines': typed_lines,
            'edges': typed_edges,
            'graphml': GraphMLFormatter.to_string(final_json['nodes'], final_json['edges'], visual=False),
            'graphml_visual': GraphMLFormatter.to_string(final_json['nodes'], final_json['edges'], visual=True),
            'stats': GraphMLFormatter.stats(final_json['nodes'], final_json['edges']),
        }

    def _extract_labels(self, full_img, validated_nodes, logger=None, on_ocr_bbox=None):
        """Run OCR on full image and match detected text to nearest symbol nodes."""
        if self._ocr is None:
            self._ocr = TrocrPIDOCR()

        ocr_results = self._ocr.run(full_img, conf_thresh=0.15, prefer_tags=True)
        if not ocr_results:
            if logger:
                logger('[OCR] No text detections found in image')
            return

        if logger:
            logger(f'[OCR] Detected {len(ocr_results)} text regions')

        img_h, img_w = full_img.shape[:2]
        max_dist = max(120, int(min(img_h, img_w) * 0.05))

        matches = self._ocr.match_to_nodes(ocr_results, validated_nodes, max_dist=max_dist)
        labels = {}
        for node_id, text, conf in matches:
            if node_id not in labels:
                labels[node_id] = []
            labels[node_id].append((text, conf))

        for node in validated_nodes:
            nid = node['id']
            if nid in labels:
                best = max(labels[nid], key=lambda x: x[1])
                node['Labels'] = best[0]
                node['ocr_confidence'] = best[1]
                node['ocr_all'] = [t for t, _ in labels[nid]]

        matched = sum(1 for n in validated_nodes if 'Labels' in n)
        if logger:
            logger(f'[OCR] {matched}/{len(validated_nodes)} symbols labeled')

        if on_ocr_bbox:
            for box, text, conf in ocr_results:
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                on_ocr_bbox(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)), text, conf)

    def _start_ocr_thread(self, full_img):
        """Start OCR in background thread. Returns (thread, result_holder)."""
        if self._ocr is None:
            self._ocr = TrocrPIDOCR()

        result = {'ocr_results': None, 'error': None}

        def _run():
            try:
                result['ocr_results'] = self._ocr.run(full_img, conf_thresh=0.15, prefer_tags=True)
            except Exception as e:
                result['error'] = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t, result

    def _get_symbol_crop(self, node, full_img=None):
        x1, y1, x2, y2 = [int(c) for c in node['coordinates']]
        if full_img is not None:
            return full_img[y1:y2, x1:x2]
        return np.zeros((max(1, y2-y1), max(1, x2-x1), 3), dtype=np.uint8)

    def _get_bbox_ratio(self, node):
        x1, y1, x2, y2 = node['coordinates']
        bw = x2 - x1
        bh = y2 - y1
        return bw / max(bh, 1)

    def reclassify_symbol(self, node_id, new_class, parent_class, validated_nodes, full_img=None):
        for node in validated_nodes:
            if node['id'] == node_id:
                crop = self._get_symbol_crop(node, full_img)
                self.class_memory.add_classification(
                    crop=crop,
                    user_class=new_class,
                    parent_class=parent_class,
                    coarse_class=str(node.get('raw_id', '')),
                    ocr_label=node.get('Labels', 'N/A'),
                    bbox_ratio=self._get_bbox_ratio(node)
                )
                node['type'] = new_class
                node['fine_class'] = new_class
                return True
        return False

    def _save_visualization(self, image_path, nodes, out_path, edges=None):
        img = cv2.imread(image_path)

        if edges:
            node_coords = {n['id']: n['coordinates'] for n in nodes}
            line_colors = {
                'process': (0, 0, 255),
                'signal': (255, 0, 0),
                'utility': (0, 200, 200),
                'software': (0, 200, 0),
                'mechanical': (0, 255, 255),
                'heat_trace': (255, 0, 255)
            }
            for src_id, tgt_id, line_type, *_ in edges:
                if src_id not in node_coords or tgt_id not in node_coords:
                    continue
                sc = node_coords[src_id]
                tc = node_coords[tgt_id]
                pt1 = (int((sc[0]+sc[2])/2), int((sc[1]+sc[3])/2))
                pt2 = (int((tc[0]+tc[2])/2), int((tc[1]+tc[3])/2))
                color = line_colors.get(line_type, (128, 128, 128))
                if line_type == 'signal':
                    dx, dy = pt2[0]-pt1[0], pt2[1]-pt1[1]
                    dist = max(1, int((dx**2+dy**2)**0.5))
                    for i in range(0, dist, 12):
                        t1, t2 = i/dist, min((i+6)/dist, 1.0)
                        p1 = (int(pt1[0]+dx*t1), int(pt1[1]+dy*t1))
                        p2 = (int(pt1[0]+dx*t2), int(pt1[1]+dy*t2))
                        cv2.line(img, p1, p2, color, 2)
                elif line_type == 'software':
                    dx, dy = pt2[0]-pt1[0], pt2[1]-pt1[1]
                    dist = max(1, int((dx**2+dy**2)**0.5))
                    for i in range(0, dist, 16):
                        t1, t2 = i/dist, min((i+10)/dist, 1.0)
                        p1 = (int(pt1[0]+dx*t1), int(pt1[1]+dy*t1))
                        p2 = (int(pt1[0]+dx*t2), int(pt1[1]+dy*t2))
                        cv2.line(img, p1, p2, color, 2)
                elif line_type == 'mechanical':
                    dx, dy = pt2[0]-pt1[0], pt2[1]-pt1[1]
                    dist = max(1, int((dx**2+dy**2)**0.5))
                    for i in range(0, dist, 20):
                        t = i/dist
                        cx = int(pt1[0]+dx*t)
                        cy = int(pt1[1]+dy*t)
                        cv2.drawMarker(img, (cx, cy), color, cv2.MARKER_TILTED_CROSS, 8, 2)
                elif line_type == 'heat_trace':
                    dx, dy = pt2[0]-pt1[0], pt2[1]-pt1[1]
                    dist = max(1, int((dx**2+dy**2)**0.5))
                    for i in range(0, dist, 8):
                        t1, t2 = i/dist, min((i+4)/dist, 1.0)
                        offset = 3 if (i//8) % 2 == 0 else -3
                        nx, ny = -dy/dist, dx/dist
                        p1 = (int(pt1[0]+dx*t1+nx*offset), int(pt1[1]+dy*t1+ny*offset))
                        p2 = (int(pt1[0]+dx*t2+nx*offset), int(pt1[1]+dy*t2+ny*offset))
                        cv2.line(img, p1, p2, color, 2)
                else:
                    thickness = 3 if line_type == 'process' else 1
                    cv2.line(img, pt1, pt2, color, thickness)

        for node in nodes:
            coords = node['coordinates']
            label = f'{node["type"]} ({node.get("Labels", "N/A")})'
            cv2.rectangle(img, (int(coords[0]), int(coords[1])), (int(coords[2]), int(coords[3])), (0, 255, 0), 4)
            cv2.putText(img, label, (int(coords[0]), int(coords[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.imwrite(out_path, img)

    def _run_coarse_scan(self, image_path, callback=None, logger=None):
        """SAHI tiled inference at 640px with 32class.pt."""
        def log(msg):
            if logger: logger(f'[SCAN] {msg}')

        all_boxes, all_scores, all_labels = [], [], []
        img = cv2.imread(image_path)
        if img is None: return []
        img_h, img_w = img.shape[:2]

        if self.sahi_available:
            try:
                from sahi.predict import get_sliced_prediction
                
                log(f"SAHI active ({self.sahi_tile_size}x{self.sahi_tile_size} tiles, 20% overlap)...")
                
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                result = get_sliced_prediction(
                    img_rgb,
                    self.detection_model,
                    slice_height=self.sahi_params['slice_height'],
                    slice_width=self.sahi_params['slice_width'],
                    overlap_height_ratio=self.sahi_params['overlap_height_ratio'],
                    overlap_width_ratio=self.sahi_params['overlap_width_ratio'],
                    perform_standard_pred=False,
                    verbose=0
                )
                
                for pred in result.object_prediction_list:
                    bbox = pred.bbox
                    x1, y1, x2, y2 = bbox.minx, bbox.miny, bbox.maxx, bbox.maxy
                    all_boxes.append([x1/img_w, y1/img_h, x2/img_w, y2/img_h])
                    all_scores.append(pred.score.value)
                    all_labels.append(pred.category.id)
                
                log(f'SAHI complete. Found {len(all_boxes)} raw detections.')
                
            except Exception as e:
                log(f'SAHI failed: {e}. Using direct YOLO inference.')
                self._run_yolo_direct(img, all_boxes, all_scores, all_labels, logger=logger)
        else:
            log("SAHI not available. Using direct YOLO inference.")
            self._run_yolo_direct(img, all_boxes, all_scores, all_labels, logger=logger)
        
        if not all_boxes:
            return []
        
        boxes, scores, labels = weighted_boxes_fusion(
            [all_boxes], [all_scores], [all_labels],
            iou_thr=0.60, skip_box_thr=0.1
        )
        log(f'WBF complete. Stabilized {len(boxes)} unique symbols.')
        
        # Containment filter
        keep = [True] * len(boxes)
        for i in range(len(boxes)):
            for j in range(len(boxes)):
                if i == j or not keep[i] or not keep[j]: continue
                b1, b2 = boxes[i], boxes[j]
                inter_x1 = max(b1[0], b2[0])
                inter_y1 = max(b1[1], b2[1])
                inter_x2 = min(b1[2], b2[2])
                inter_y2 = min(b1[3], b2[3])
                
                inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
                area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
                area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
                
                if area2 > 0 and (inter_area / area2) > 0.7:
                    keep[j] = False
                elif area1 > 0 and (inter_area / area1) > 0.7:
                    keep[i] = False
        
        results = []
        for i in range(len(boxes)):
            if keep[i]:
                results.append({
                    'bbox': [boxes[i][0]*img_w, boxes[i][1]*img_h, boxes[i][2]*img_w, boxes[i][3]*img_h],
                    'class': int(labels[i]),
                    'conf': scores[i]
                })
                if callback:
                    name = self._class_names.get(int(labels[i]), '?')
                    b = boxes[i]
                    callback([b[0]*img_w, b[1]*img_h, b[2]*img_w, b[3]*img_h, name])
        
        return results

    def _run_yolo_direct(self, img, all_boxes, all_scores, all_labels, logger=None):
        """Fallback direct YOLO inference when SAHI is unavailable."""
        img_h, img_w = img.shape[:2]
        results = self.model_coarse.predict(img, imgsz=self.sahi_tile_size, conf=0.1, verbose=False)
        for res in results:
            for box in res.boxes:
                b = box.xyxy[0].cpu().numpy()
                all_boxes.append([b[0]/img_w, b[1]/img_h, b[2]/img_w, b[3]/img_h])
                all_scores.append(float(box.conf[0]))
                all_labels.append(int(box.cls[0]))

    def _is_on_pipeline(self, bbox, lines, threshold=75):
        for p1, p2 in lines:
            if TopologyEngine._dist_to_bbox(p1, bbox) < threshold or TopologyEngine._dist_to_bbox(p2, bbox) < threshold:
                return True
            mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            if TopologyEngine._dist_to_bbox(mid, bbox) < threshold:
                return True
        return False

    @staticmethod
    def _is_plausible_symbol(bbox, img_h):
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        return w > 5 and h > 5

    def _map_class(self, class_id):
        name = self._class_names.get(class_id)
        if name is not None:
            return name.lower().replace(" ", "_")
        return "general"

    def classify_symbol(self, node, full_img=None):
        crop = self._get_symbol_crop(node, full_img)
        if crop is None or crop.size == 0:
            return node.get('type', 'general')
        
        match = self.class_memory.find_match(
            crop=crop,
            coarse_class=str(node.get('raw_id', '')),
            threshold=0.65
        )
        if match:
            return match['user_class']
        
        coarse_name = self._map_class(node.get('class', -1))
        result = self.rag.classify(crop, coarse_class=coarse_name, threshold=0.50)
        if result['confidence'] > 0.50:
            node['rag_confidence'] = result['confidence']
            node['rag_ambiguous'] = result['ambiguous']
            return result['class_name']
        
        return node.get('type', 'general')

    def _merge_tag_segments(self, nodes, log=None):
        """Merge split instrument tag detections (e.g., 'PDL' + '824' → 'PDL 824')."""
        TAG_PREFIXES = {
            # Pressure
            'P', 'PT', 'PD', 'PDI', 'PDL', 'PDT', 'PI', 'PE', 'PC', 'PCV', 'PIC', 'PIT',
            'PS', 'PSH', 'PSL', 'PSLL', 'PSHH', 'PSD', 'PSV', 'PR', 'PXR',
            # Flow
            'F', 'FT', 'FI', 'FE', 'FC', 'FCV', 'FIC', 'FIT', 'FS', 'FSH', 'FSL', 'FF', 'FY',
            # Level
            'L', 'LT', 'LI', 'LE', 'LC', 'LCV', 'LIC', 'LIT', 'LS', 'LSH', 'LSL', 'LSLL',
            'LAL', 'LAH', 'LAHH', 'LALL', 'LX', 'LY',
            # Temperature
            'T', 'TT', 'TI', 'TE', 'TC', 'TCV', 'TIC', 'TIT', 'TS', 'TSH', 'TSL', 'TX', 'TY',
            # Analytical
            'A', 'AT', 'AI', 'AE', 'AC', 'ACV', 'AIC', 'AIT',
            # Speed/Position
            'S', 'ST', 'SI', 'SE', 'SC', 'SCV', 'SIC', 'SIT', 'SS', 'SSH', 'SSL',
            # Vibration
            'V', 'VT', 'VI', 'VE', 'VC', 'VCV', 'VIC', 'VIT',
            # Voltage/Current
            'E', 'ET', 'EI', 'EE', 'EC', 'ECV', 'EIC', 'EIT',
            # Weight/Force
            'W', 'WT', 'WI', 'WE', 'WC', 'WCV', 'WIC', 'WIT',
            # Hand/Manual
            'H', 'HS', 'HC', 'HCV', 'HSK',
            # Combustion
            'B', 'BT', 'BI', 'BE', 'BC', 'BCV', 'BIC', 'BIT',
            # Driver
            'D', 'DT', 'DI', 'DE', 'DC', 'DCV', 'DIC', 'DIT',
            # Computer/Console
            'C', 'CI', 'CO', 'CS',
            # Indicator
            'I', 'IC', 'IY',
            # Relay/Computer
            'R', 'RC', 'RY',
            # Switch
            'SW',
            # Record/Controller
            'K', 'KC', 'KCS', 'KY',
            # Sound
            'Z', 'ZT', 'ZI', 'ZE', 'ZC',
            # Unclassified
            'X', 'XT', 'XI', 'XE', 'XC',
            # Multi-letter
            'GRL', 'DDL', 'CDL', 'EDL', 'VDL', 'WDL', 'SDL', 'TDL', 'LDL', 'FDL',
            'PSL', 'PDL', 'FSL', 'LSL', 'TSL', 'ASL', 'SSL', 'VSL', 'ESL', 'WSL',
            'PSH', 'PDH', 'FSH', 'LSH', 'TSH', 'ASH', 'SSH', 'VSH', 'ESH', 'WSH',
        }
        
        def is_tag_prefix(text):
            clean = text.strip().upper()
            return clean in TAG_PREFIXES
        
        def is_numeric(text):
            clean = text.strip().replace('.', '').replace('-', '')
            return clean.isdigit() and len(clean) >= 1
        
        def bbox_center(box):
            x1, y1, x2, y2 = box
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        
        def bbox_distance(b1, b2):
            c1 = bbox_center(b1)
            c2 = bbox_center(b2)
            return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)**0.5
        
        def bbox_union(b1, b2):
            return [min(b1[0], b2[0]), min(b1[1], b2[1]), 
                    max(b1[2], b2[2]), max(b1[3], b2[3])]
        
        prefix_nodes = []
        number_nodes = []
        for i, node in enumerate(nodes):
            label = node.get('Labels', '').strip()
            if not label:
                continue
            if is_tag_prefix(label):
                prefix_nodes.append((i, node))
            elif is_numeric(label):
                number_nodes.append((i, node))
        
        if not prefix_nodes or not number_nodes:
            return nodes
        
        merges = []
        used_numbers = set()
        
        for p_idx, p_node in prefix_nodes:
            p_box = p_node['coordinates']
            best_dist = float('inf')
            best_n_idx = None
            
            for n_idx, n_node in number_nodes:
                if n_idx in used_numbers:
                    continue
                n_box = n_node['coordinates']
                dist = bbox_distance(p_box, n_box)
                
                p_cx, p_cy = bbox_center(p_box)
                n_cx, n_cy = bbox_center(n_box)
                vertical_overlap = abs(p_cx - n_cx) < max(abs(p_box[2]-p_box[0]), abs(n_box[2]-n_box[0])) * 0.5
                close_enough = dist < max(abs(p_box[3]-p_box[1]), abs(n_box[3]-n_box[1])) * 2.5
                
                if vertical_overlap and close_enough and dist < best_dist:
                    best_dist = dist
                    best_n_idx = n_idx
            
            if best_n_idx is not None:
                merges.append((p_idx, best_n_idx))
                used_numbers.add(best_n_idx)
        
        if not merges:
            return nodes
        
        merged_indices = set()
        for p_idx, n_idx in merges:
            p_node = nodes[p_idx]
            n_node = nodes[n_idx]
            
            new_label = f"{p_node['Labels'].strip()} {n_node['Labels'].strip()}"
            p_node['Labels'] = new_label
            p_node['coordinates'] = bbox_union(p_node['coordinates'], n_node['coordinates'])
            if 'ocr_all' in p_node and 'ocr_all' in n_node:
                p_node['ocr_all'] = list(set(p_node['ocr_all'] + n_node['ocr_all']))
            merged_indices.add(n_idx)
        
        result = [n for i, n in enumerate(nodes) if i not in merged_indices]
        
        if log:
            log(f'[TAG MERGE] Merged {len(merges)} split tags')
        
        return result

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    model = os.getenv("PT_MODEL_PATH", "models/32class.pt")
    img = sys.argv[1] if len(sys.argv) > 1 else "assets/class_gallery/Centrifugal_pump.png"
    engine = UniversalEngine(model)
    engine.process(img)
