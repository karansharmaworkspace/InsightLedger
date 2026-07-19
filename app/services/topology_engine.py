"""
P&ID Topology Engine: Line detection, classification, and connectivity inference.
Production module extracted from Digitwin Technologies DPID AI.
"""

import cv2
import numpy as np
import math
import re
from collections import defaultdict

# ── Line-type detection constants ─────────────────────────────────────────
_THICKNESS_SAMPLES = 5     # number of perpendicular samples per segment
_DASH_WINDOW = 9           # pixels to scan along line for dash detection
_SOLID_FRACTION = 0.85     # ≥85% filled → "solid"

# ── Symbol categories for ISA-5.1 line classification ─────────────────────
# Equipment symbols (process lines connect these)
_EQUIPMENT_SYMBOLS = {
    "pump", "centrifugal_pump", "rotary_pump", "gear_pump", "diaphragm_pump",
    "valve", "gate_valve", "globe_valve", "ball_valve", "butterfly_valve",
    "check_valve", "control_valve", "safety_valve", "relief_valve",
    "vessel", "tank", "column", "reactor", "drum", "separator",
    "heat_exchanger", "shell_tube", "plate_exchanger", "air_cooler",
    "compressor", "centrifugal_compressor", "reciprocating_compressor",
    "filter", "strainer", "basket", "cartridge",
    "mixer", "agitator", "blender",
    "crusher", "grinder", "mill",
    "dryer", "evaporator", "distillation",
    "furnace", "boiler", "heater",
    "conveyor", "elevator",
    "motor", "engine", "turbine",
    "fan", "blower",
}

# Instrument symbols (signal lines connect these)
_INSTRUMENT_SYMBOLS = {
    "instrument", "indicator", "transmitter", "controller", "recorder",
    "gauge", "switch", "alarm", "meter", "sensor", "element", "transducer",
    "flow_indicator", "level_indicator", "pressure_indicator", "temperature_indicator",
    "flow_transmitter", "level_transmitter", "pressure_transmitter", "temperature_transmitter",
    "flow_controller", "level_controller", "pressure_controller", "temperature_controller",
    "flow_switch", "level_switch", "pressure_switch", "temperature_switch",
    "flow_meter", "level_meter", "pressure_meter", "temperature_meter",
}

# Utility source symbols
_UTILITY_SOURCE_SYMBOLS = {
    "steam_source", "air_source", "water_source", "gas_source",
    "nitrogen_source", "hydrogen_source", "oxygen_source",
    "utility_header", "drain", "vent", "flare",
}

# Utility destination symbols (things that USE utilities)
_UTILITY_DEST_SYMBOLS = {
    "steam_trap", "condensate", "drain", "vent",
    "relief_valve", "safety_valve",
}

# Instrument keywords for class name detection
_INSTRUMENT_KEYWORDS = {
    "indicator", "transmitter", "controller", "recorder", "gauge",
    "switch", "alarm", "meter", "sensor", "element", "transducer",
    "flow", "level", "pressure", "temperature",
}

# ISA-5.1 instrument tag regex: matches patterns like LIC-101, TI-102, PDIT-204
_INSTRUMENT_TAG_RE = re.compile(r'^(?P<type>[A-Z]{2,4})-(?P<loop>\d{2,4})$')


def _get_symbol_category(sym):
    """Determine if a symbol is equipment, instrument, or utility source."""
    if not sym:
        return "unknown"
    
    # Check various name fields
    name = ""
    for field in ["type", "type_key", "fine_class", "Labels", "class_name"]:
        val = sym.get(field, "")
        if val and val != "N/A":
            name = val.lower()
            break
    
    if not name:
        return "unknown"
    
    # Check instrument first (more specific)
    for kw in _INSTRUMENT_SYMBOLS:
        if kw in name:
            return "instrument"
    
    # Check equipment
    for kw in _EQUIPMENT_SYMBOLS:
        if kw in name:
            return "equipment"
    
    # Check utility source
    for kw in _UTILITY_SOURCE_SYMBOLS:
        if kw in name:
            return "utility_source"
    
    return "unknown"


def _find_symbols_near_endpoint(p, symbols, threshold=80):
    """Find symbols whose bbox center is within threshold pixels of point p."""
    px, py = p
    nearby = []
    
    for sym in symbols:
        bbox = sym.get("bbox", sym.get("coordinates", [0,0,0,0]))
        if len(bbox) < 4:
            continue
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        dist = math.hypot(px - cx, py - cy)
        if dist < threshold:
            nearby.append(sym)
    
    return nearby


def classify_line_by_symbols(p1, p2, symbols, thresh_img):
    """Classify line type using pixel heuristics + symbol context.
    
    ISA-5.1 line types:
    - process: thick, solid → material flow
    - signal: thin, dashed/dotted → instrument signals
    - utility: thin, solid → steam, water, air
    - software: dash-dot-dot → digital/data links
    - mechanical: X markers → shafts, belts
    - heat_trace: zigzag/wavy → heat tracing
    """
    # Get pixel-based classification first
    pixel_lt, pixel_st = TopologyEngine.classify_line_type(p1, p2, thresh_img)
    
    if not symbols:
        return pixel_lt, pixel_st
    
    # Find symbols near each endpoint
    syms_start = _find_symbols_near_endpoint(p1, symbols, threshold=100)
    syms_end = _find_symbols_near_endpoint(p2, symbols, threshold=100)
    syms_all = syms_start + syms_end
    
    cats_start = [_get_symbol_category(s) for s in syms_start]
    cats_end = [_get_symbol_category(s) for s in syms_end]
    
    has_instrument = "instrument" in cats_start or "instrument" in cats_end
    has_equipment = "equipment" in cats_start or "equipment" in cats_end
    has_utility_source = "utility_source" in cats_start or "utility_source" in cats_end
    
    # ── Symbol-aware overrides ──
    
    # Instrument connected → signal (override thick lines misclassified as process)
    if has_instrument:
        # Determine subtype from instrument type
        for s in syms_all:
            name = _get_symbol_name(s)
            
            if "transmitter" in name:
                return "signal", 2   # dotted
            elif "controller" in name:
                return "signal", 8   # dash-dot ( pneumatic )
            elif "recorder" in name:
                return "signal", 3   # 2s_signal
            elif any(kw in name for kw in ("indicator", "gauge", "meter")):
                if pixel_lt == "signal":
                    return pixel_lt, pixel_st
                return "signal", 1   # continuous thin
            elif "switch" in name:
                return "signal", 4   # x_signal
            elif "alarm" in name:
                return "signal", 5   # o_signal
        
        # Default: keep pixel subtype if signal, otherwise signal continuous
        if pixel_lt == "signal":
            return pixel_lt, pixel_st
        return "signal", 1
    
    # Utility source connected → utility
    if has_utility_source and pixel_lt != "process":
        return "utility", 0
    
    # Equipment-to-equipment with thin line → still process (override)
    if has_equipment and pixel_lt == "utility":
        # Check if both endpoints have equipment
        if "equipment" in cats_start and "equipment" in cats_end:
            return "process", 1
    
    # ── Return pixel-based result for all other cases ──
    return pixel_lt, pixel_st


def _get_symbol_name(sym):
    for field in ["type", "type_key", "fine_class", "Labels"]:
        val = sym.get(field, "")
        if val and val != "N/A":
            return val.lower()
    return ""

LINE_SUBTYPES = {
    1: "continuous",
    2: "dotted",
    3: "2s_signal",
    4: "x_signal",
    5: "o_signal",
    6: "wavy",
    7: "turning",
    8: "1s_signal",
    9: "arrow",
    10: "2_slash",
    11: "software_link",
    12: "mechanical",
    13: "heat_trace",
    14: "dash_dot_dot",
}


def _sample_along_line(p1, p2, step=5):
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1: return []
    ux, uy = dx / length, dy / length
    pts = []
    for t in range(0, int(length), step):
        pts.append((int(x1 + ux * t), int(y1 + uy * t)))
    return pts


def _detect_waviness(p1, p2, thresh_img, amplitude_thresh=3):
    pts = _sample_along_line(p1, p2, step=3)
    if len(pts) < 10: return False, 0.0
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1: return False, 0.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    deviations = []
    for cx, cy in pts:
        proj = (cx - x1) * ux + (cy - y1) * uy
        expected_x = x1 + ux * proj
        expected_y = y1 + uy * proj
        dev = (cx - expected_x) * px + (cy - expected_y) * py
        deviations.append(dev)
    if len(deviations) < 6: return False, 0.0
    sign_changes = sum(1 for i in range(1, len(deviations)) 
                       if deviations[i] * deviations[i-1] < 0)
    avg_amp = sum(abs(d) for d in deviations) / len(deviations)
    freq = sign_changes / (len(deviations) - 1)
    is_wavy = sign_changes >= 4 and avg_amp >= amplitude_thresh and freq > 0.15
    return is_wavy, freq


def _detect_markers(p1, p2, thresh_img, marker_type="x"):
    h, w = thresh_img.shape[:2]
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 40: return 0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    marker_count = 0
    scan_step = max(25, int(length / 6))
    for t in range(scan_step, int(length) - scan_step, scan_step):
        cx = int(x1 + ux * t)
        cy = int(y1 + uy * t)
        if not (8 <= cx < w-8 and 8 <= cy < h-8): continue
        region = thresh_img[cy-8:cy+8, cx-8:cx+8]
        if region.size == 0: continue
        if marker_type == "x":
            diag1 = np.sum(np.diag(region) > 0)
            diag2 = np.sum(np.diag(np.fliplr(region)) > 0)
            center = region[7, 7] if region.shape[0] > 14 and region.shape[1] > 14 else 0
            if diag1 >= 5 and diag2 >= 5 and center > 0:
                marker_count += 1
        elif marker_type == "o":
            center_val = region[7, 7] if region.shape[0] > 14 and region.shape[1] > 14 else 255
            ring = np.sum(region > 0)
            if ring > 20 and center_val == 0:
                marker_count += 1
        elif marker_type == "slash":
            slash1 = np.sum(np.diag(region) > 0)
            slash2 = np.sum(np.diag(region[::2, ::2]) > 0)
            if slash1 >= 4 and slash2 >= 2:
                marker_count += 1
    return marker_count


def _detect_dash_dot_dot(p1, p2, thresh_img):
    """Detect dash-dot-dot pattern (software/data links)."""
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 40:
        return False
    
    ux, uy = dx / length, dy / length
    h, w = thresh_img.shape[:2]
    
    segments = []
    in_seg = False
    seg_start = 0
    for t in range(0, int(length)):
        cx = int(x1 + ux * t)
        cy = int(y1 + uy * t)
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        filled = thresh_img[cy, cx] > 0
        if filled and not in_seg:
            seg_start = t
            in_seg = True
        elif not filled and in_seg:
            segments.append((seg_start, t))
            in_seg = False
    if in_seg:
        segments.append((seg_start, int(length)))
    
    if len(segments) < 3:
        return False
    
    seg_lens = [e - s for s, e in segments]
    gaps = []
    for i in range(1, len(segments)):
        gaps.append(segments[i][0] - segments[i-1][1])
    
    if len(gaps) < 2:
        return False
    
    avg_seg = sum(seg_lens) / len(seg_lens)
    avg_gap = sum(gaps) / len(gaps)
    
    if avg_gap < 1:
        return False
    
    ratio = avg_seg / avg_gap
    return 0.3 < ratio < 1.5 and len(segments) >= 4


def _detect_mechanical_markers(p1, p2, thresh_img):
    """Detect mechanical markers (X on line for shafts/belts)."""
    x_count = _detect_markers(p1, p2, thresh_img, "x")
    return x_count >= 2


def _detect_heat_trace(p1, p2, thresh_img):
    """Detect heat trace (zigzag/wavy overlay on existing line)."""
    is_wavy, freq = _detect_waviness(p1, p2, thresh_img, amplitude_thresh=2)
    if not is_wavy:
        return False
    
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    
    ux, uy = dx / length, dy / length
    h, w = thresh_img.shape[:2]
    
    thicknesses = []
    for i in range(5):
        t = (i + 1) * length / 6
        cx = int(x1 + ux * t)
        cy = int(y1 + uy * t)
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        left = 0
        for k in range(1, 15):
            sx = int(cx - uy * k)
            sy = int(cy + ux * k)
            if not (0 <= sx < w and 0 <= sy < h):
                break
            if thresh_img[sy, sx] == 0:
                break
            left = k
        right = 0
        for k in range(1, 15):
            sx = int(cx + uy * k)
            sy = int(cy - ux * k)
            if not (0 <= sx < w and 0 <= sy < h):
                break
            if thresh_img[sy, sx] == 0:
                break
            right = k
        thicknesses.append(left + right + 1)
    
    if not thicknesses:
        return False
    
    avg_thickness = sum(thicknesses) / len(thicknesses)
    return avg_thickness >= 5


def _detect_arrowhead(p1, p2, thresh_img):
    h, w = thresh_img.shape[:2]
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 20: return False
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    tip_x, tip_y = int(x2), int(y2)
    if not (10 <= tip_x < w-10 and 10 <= tip_y < h-10): return False
    arrow_len = min(15, int(length * 0.2))
    arrow_width = min(10, int(length * 0.15))
    counts = []
    for sign in [-1, 1]:
        ax = int(tip_x - ux * arrow_len + px * sign * arrow_width)
        ay = int(tip_y - uy * arrow_len + py * sign * arrow_width)
        if 0 <= ax < w and 0 <= ay < h:
            counts.append(thresh_img[ay, ax] > 0)
    return sum(counts) >= 1


def _detect_turning(p1, p2, thresh_img):
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 80: return False
    h, w = thresh_img.shape[:2]
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    seg1_dev = 0
    seg2_dev = 0
    quarter = int(length / 4)
    for t in range(quarter - 10, quarter + 10):
        cx = int(x1 + ux * t)
        cy = int(y1 + uy * t)
        if not (0 <= cx < w and 0 <= cy < h): continue
        for k in range(-12, 13):
            sx = int(cx + px * k)
            sy = int(cy + py * k)
            if 0 <= sx < w and 0 <= sy < h and thresh_img[sy, sx] > 0:
                seg1_dev = max(seg1_dev, abs(k))
    three_quarter = int(length * 3 / 4)
    for t in range(three_quarter - 10, three_quarter + 10):
        cx = int(x1 + ux * t)
        cy = int(y1 + uy * t)
        if not (0 <= cx < w and 0 <= cy < h): continue
        for k in range(-12, 13):
            sx = int(cx + px * k)
            sy = int(cy + py * k)
            if 0 <= sx < w and 0 <= sy < h and thresh_img[sy, sx] > 0:
                seg2_dev = max(seg2_dev, abs(k))
    return seg1_dev > 10 and seg2_dev > 10 and abs(seg1_dev - seg2_dev) > 5


def _detect_dash_pattern(p1, p2, thresh_img):
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 20: return "solid", 1.0, 1.0
    ux, uy = dx / length, dy / length
    h, w = thresh_img.shape[:2]
    segments = []
    in_seg = False
    seg_start = 0
    for t in range(0, int(length)):
        cx = int(x1 + ux * t)
        cy = int(y1 + uy * t)
        if not (0 <= cx < w and 0 <= cy < h): continue
        filled = thresh_img[cy, cx] > 0
        if filled and not in_seg:
            seg_start = t
            in_seg = True
        elif not filled and in_seg:
            segments.append((seg_start, t))
            in_seg = False
    if in_seg:
        segments.append((seg_start, int(length)))
    if len(segments) < 2:
        return "solid", 1.0, 0.0
    seg_lens = [e - s for s, e in segments]
    gaps = []
    for i in range(1, len(segments)):
        gaps.append(segments[i][0] - segments[i-1][1])
    avg_seg = sum(seg_lens) / len(seg_lens) if seg_lens else 0
    avg_gap = sum(gaps) / len(gaps) if gaps else 0
    if avg_gap < 1: return "solid", 1.0, 0.0
    ratio = avg_seg / avg_gap if avg_gap > 0 else 10
    if ratio > 3:
        return "solid", 1.0, 0.0
    elif 1.5 < ratio <= 3:
        return "dash_dot", avg_seg, avg_gap
    else:
        return "dashed", avg_seg, avg_gap


class TopologyEngine:
    @staticmethod
    def merge_segments(segments, angle_thresh=25, gap_thresh=50):
        """Merge collinear, nearby segments into longer lines using Union-Find."""
        if not segments:
            return []

        n = len(segments)
        segs = []
        for (p1, p2) in segments:
            x1, y1 = p1
            x2, y2 = p2
            if (x1, y1) > (x2, y2):
                x1, y1, x2, y2 = x2, y2, x1, y1
            length = np.hypot(x2-x1, y2-y1)
            angle = np.degrees(np.arctan2(y2-y1, x2-x1)) % 180
            segs.append((x1, y1, x2, y2, angle, length))

        # Spatial grid for fast neighbor lookup
        GRID = 50
        grid = defaultdict(list)
        for i, s in enumerate(segments):
            for px, py in [s[0], s[1]]:
                cell = (int(px // GRID), int(py // GRID))
                grid[cell].append(i)

        # Union-Find
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        checked = set()
        for i in range(n):
            si = segs[i]
            candidates = set()
            for px, py in [(si[0], si[1]), (si[2], si[3])]:
                cell = (int(px // GRID), int(py // GRID))
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        for j in grid.get((cell[0]+dx, cell[1]+dy), []):
                            if j != i:
                                candidates.add(j)

            for j in candidates:
                pair = (min(i,j), max(i,j))
                if pair in checked:
                    continue
                checked.add(pair)
                sj = segs[j]

                angle_diff = abs(si[4] - sj[4])
                if angle_diff > 90:
                    angle_diff = 180 - angle_diff
                if angle_diff > angle_thresh:
                    continue

                endpoints_i = [(si[0], si[1]), (si[2], si[3])]
                endpoints_j = [(sj[0], sj[1]), (sj[2], sj[3])]
                min_gap = min(np.hypot(pi[0]-pj[0], pi[1]-pj[1])
                              for pi in endpoints_i for pj in endpoints_j)

                if min_gap < gap_thresh:
                    union(i, j)

        # Collect merged lines
        components = defaultdict(list)
        for i in range(n):
            components[find(i)].append(i)

        merged = []
        for root, members in components.items():
            all_pts = []
            for idx in members:
                s = segs[idx]
                all_pts.append((s[0], s[1]))
                all_pts.append((s[2], s[3]))
            if len(all_pts) < 2:
                continue

            avg_angle = np.radians(segs[members[0]][4])
            ux, uy = np.cos(avg_angle), np.sin(avg_angle)
            projections = [(p[0]*ux + p[1]*uy, p) for p in all_pts]
            projections.sort(key=lambda x: x[0])

            p_start = projections[0][1]
            p_end = projections[-1][1]
            merged_len = np.hypot(p_end[0]-p_start[0], p_end[1]-p_start[1])
            if merged_len > 20:
                merged.append(((int(p_start[0]), int(p_start[1])),
                              (int(p_end[0]), int(p_end[1]))))

        return merged

    @staticmethod
    def find_lines(image_path, symbol_bboxes=None):
        img = cv2.imread(image_path)
        if img is None: return []
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        h, w = gray.shape

        all_segments = []
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))

        for thresh_val in [200, None]:
            if thresh_val is None:
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            else:
                _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)

            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            lines = cv2.HoughLinesP(closed, rho=1, theta=np.pi/180,
                                    threshold=50, minLineLength=30, maxLineGap=30)
            if lines is not None:
                for line in lines:
                    coords = line[0] if hasattr(line[0], '__len__') else line
                    x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                    length = np.hypot(x2 - x1, y2 - y1)
                    if length > min(w, h) * 0.8:
                        continue
                    margin = 20
                    if (x1 < margin and x2 < margin) or (x1 > w - margin and x2 > w - margin):
                        continue
                    if (y1 < margin and y2 < margin) or (y1 > h - margin and y2 > h - margin):
                        continue
                    all_segments.append(((x1, y1), (x2, y2)))

        unique = []
        seen = set()
        for seg in all_segments:
            key = (seg[0][0]//5*5, seg[0][1]//5*5, seg[1][0]//5*5, seg[1][1]//5*5)
            if key not in seen:
                seen.add(key)
                unique.append(seg)

        if symbol_bboxes:
            unique = TopologyEngine._filter_lines_in_boxes(unique, symbol_bboxes)

        unique = TopologyEngine.merge_segments(unique)
        return unique

    @staticmethod
    def find_lines_symbol_guided(image_path, symbol_bboxes, connections=None, margin=50):
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None: return []
        h, w = gray.shape
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        if not symbol_bboxes:
            return TopologyEngine.find_lines(image_path)
        
        bboxes = []
        for bbox in symbol_bboxes:
            if isinstance(bbox, dict):
                bboxes.append(bbox)
            elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                bboxes.append({"xmin": bbox[0], "ymin": bbox[1], "xmax": bbox[2], "ymax": bbox[3]})
        
        if not bboxes:
            return TopologyEngine.find_lines(image_path)
        
        segments = []
        lines = cv2.HoughLinesP(
            thresh, rho=1, theta=np.pi/180,
            threshold=50, minLineLength=30, maxLineGap=15
        )
        
        if lines is None:
            return []
        
        all_segments = []
        for line in lines:
            coords = line[0] if hasattr(line[0], '__len__') else line
            x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
            length = np.hypot(x2 - x1, y2 - y1)
            if length < 20:
                continue
            all_segments.append(((x1, y1), (x2, y2)))
        
        symbol_centers = []
        for bbox in bboxes:
            cx = (bbox["xmin"] + bbox["xmax"]) / 2
            cy = (bbox["ymin"] + bbox["ymax"]) / 2
            symbol_centers.append((cx, cy, bbox))
        
        for seg in all_segments:
            (sx1, sy1), (sx2, sy2) = seg
            seg_mid_x = (sx1 + sx2) / 2
            seg_mid_y = (sy1 + sy2) / 2
            
            near_symbols = []
            for cx, cy, bbox in symbol_centers:
                dist_to_seg = np.hypot(seg_mid_x - cx, seg_mid_y - cy)
                bbox_radius = np.hypot(bbox["xmax"] - bbox["xmin"], bbox["ymax"] - bbox["ymin"]) / 2
                if dist_to_seg < bbox_radius + margin * 3:
                    near_symbols.append((cx, cy, bbox))
            
            if len(near_symbols) >= 1:
                s1 = near_symbols[0]
                
                s1_cx, s1_cy = s1[0], s1[1]
                
                seg_angle = np.arctan2(sy2 - sy1, sx2 - sx1)
                sym_angle = np.arctan2(s1_cy - sy1, s1_cx - sx1)
                
                angle_diff = abs(seg_angle - sym_angle)
                if angle_diff > np.pi:
                    angle_diff = 2 * np.pi - angle_diff
                
                if angle_diff < np.pi / 2 or len(near_symbols) >= 2:
                    segments.append(seg)
        
        return segments

    @staticmethod
    def trace_pipe_path(image_path, bbox1, bbox2, thickness=3):
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None: return []
        
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        cx1 = (bbox1["xmin"] + bbox1["xmax"]) / 2
        cy1 = (bbox1["ymin"] + bbox1["ymax"]) / 2
        cx2 = (bbox2["xmin"] + bbox2["xmax"]) / 2
        cy2 = (bbox2["ymin"] + bbox2["ymax"]) / 2
        
        x1_min, y1_min = int(bbox1["xmin"]), int(bbox1["ymin"])
        x1_max, y1_max = int(bbox1["xmax"]), int(bbox1["ymax"])
        x2_min, y2_min = int(bbox2["xmin"]), int(bbox2["ymin"])
        x2_max, y2_max = int(bbox2["xmax"]), int(bbox2["ymax"])
        
        margin = 30
        search_x_min = max(0, min(x1_min, x2_min) - margin)
        search_y_min = max(0, min(y1_min, y2_min) - margin)
        search_x_max = min(thresh.shape[1], max(x1_max, x2_max) + margin)
        search_y_max = min(thresh.shape[0], max(y1_max, y2_max) + margin)
        
        roi = thresh[int(search_y_min):int(search_y_max), int(search_x_min):int(search_x_max)]
        
        kernel = np.ones((3, 3), np.uint8)
        roi_clean = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, kernel)
        roi_clean = cv2.morphologyEx(roi_clean, cv2.MORPH_OPEN, kernel)
        
        start_x = int(cx1 - search_x_min)
        start_y = int(cy1 - search_y_min)
        end_x = int(cx2 - search_x_min)
        end_y = int(cy2 - search_y_min)
        
        h, w = roi_clean.shape
        start_x = max(0, min(w-1, start_x))
        start_y = max(0, min(h-1, start_y))
        end_x = max(0, min(w-1, end_x))
        end_y = max(0, min(h-1, end_y))
        
        if roi_clean[start_y, start_x] == 0:
            search_radius = 20
            for dy in range(-search_radius, search_radius+1):
                for dx in range(-search_radius, search_radius+1):
                    ny, nx = start_y+dy, start_x+dx
                    if 0 <= ny < h and 0 <= nx < w and roi_clean[ny, nx] > 0:
                        start_y, start_x = ny, nx
                        break
                else:
                    continue
                break
        
        if roi_clean[end_y, end_x] == 0:
            search_radius = 20
            for dy in range(-search_radius, search_radius+1):
                for dx in range(-search_radius, search_radius+1):
                    ny, nx = end_y+dy, end_x+dx
                    if 0 <= ny < h and 0 <= nx < w and roi_clean[ny, nx] > 0:
                        end_y, end_x = ny, nx
                        break
                else:
                    continue
                break
        
        if roi_clean[start_y, start_x] == 0 or roi_clean[end_y, end_x] == 0:
            return []
        
        cost_map = np.where(roi_clean > 0, 1, 100).astype(np.float32)
        
        from collections import deque
        visited = np.zeros_like(cost_map, dtype=bool)
        dist = np.full_like(cost_map, np.inf, dtype=np.float32)
        prev = np.full((*cost_map.shape, 2), -1, dtype=np.int32)
        
        dist[start_y, start_x] = 0
        pq = deque([(0, start_x, start_y)])
        
        directions = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
        
        while pq:
            d, x, y = pq.popleft()
            
            if visited[y, x]:
                continue
            visited[y, x] = True
            
            if x == end_x and y == end_y:
                break
            
            for dx, dy in directions:
                nx, ny = x+dx, y+dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                    new_dist = d + cost_map[ny, nx]
                    if new_dist < dist[ny, nx]:
                        dist[ny, nx] = new_dist
                        prev[ny, nx] = [x, y]
                        pq.append((new_dist, nx, ny))
        
        if not visited[end_y, end_x]:
            return []
        
        path = []
        cx, cy = end_x, end_y
        while cx != -1 and cy != -1:
            path.append((int(cx + search_x_min), int(cy + search_y_min)))
            px, py = prev[cy, cx]
            cx, cy = int(px), int(py)
            if cx == start_x and cy == start_y:
                path.append((int(cx + search_x_min), int(cy + search_y_min)))
                break
        
        path.reverse()
        return path

    @staticmethod
    def classify_lines(segments, image_path, symbols=None):
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return [(s[0], s[1], "utility", 0) for s in segments]

        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        result = []
        for p1, p2 in segments:
            if symbols:
                lt, subtype = classify_line_by_symbols(p1, p2, symbols, thresh)
            else:
                lt, subtype = TopologyEngine.classify_line_type(p1, p2, thresh)
            result.append((p1, p2, lt, subtype))
        return result

    @staticmethod
    def classify_line_type(p1, p2, thresh_img):
        x1, y1 = p1
        x2, y2 = p2
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 5:
            return "utility", 0

        ux, uy = dx / length, dy / length
        px, py = -uy, ux

        h, w = thresh_img.shape[:2]

        thicknesses = []
        for i in range(_THICKNESS_SAMPLES):
            t = (i + 1) * length / (_THICKNESS_SAMPLES + 1)
            cx = int(x1 + ux * t)
            cy = int(y1 + uy * t)
            if not (0 <= cx < w and 0 <= cy < h):
                continue
            left = 0
            for k in range(1, 20):
                sx = int(cx - px * k)
                sy = int(cy - py * k)
                if not (0 <= sx < w and 0 <= sy < h): break
                if thresh_img[sy, sx] == 0: break
                left = k
            right = 0
            for k in range(1, 20):
                sx = int(cx + px * k)
                sy = int(cy + py * k)
                if not (0 <= sx < w and 0 <= sy < h): break
                if thresh_img[sy, sx] == 0: break
                right = k
            thicknesses.append(left + right + 1)

        if not thicknesses:
            return "utility", 0
        avg_thickness = sum(thicknesses) / len(thicknesses)

        filled = 0
        total_samples = 0
        for step in range(0, int(length), _DASH_WINDOW):
            cx = int(x1 + ux * step)
            cy = int(y1 + uy * step)
            if not (0 <= cx < w and 0 <= cy < h): continue
            if thresh_img[cy, cx] > 0:
                filled += 1
            total_samples += 1

        if total_samples == 0:
            return "utility", 0
        fill_ratio = filled / total_samples
        is_solid = fill_ratio >= _SOLID_FRACTION

        if avg_thickness >= 4.0 and is_solid:
            return "process", 1

        is_wavy, wave_freq = _detect_waviness(p1, p2, thresh_img)
        if is_wavy:
            is_heat_trace = _detect_heat_trace(p1, p2, thresh_img)
            if is_heat_trace:
                return "heat_trace", 13
            return "signal", 6

        is_turning = _detect_turning(p1, p2, thresh_img)
        if is_turning:
            return "signal", 7

        dash_type, avg_seg, avg_gap = _detect_dash_pattern(p1, p2, thresh_img)

        is_dash_dot_dot = _detect_dash_dot_dot(p1, p2, thresh_img)
        if is_dash_dot_dot:
            return "software", 11

        is_mech = _detect_mechanical_markers(p1, p2, thresh_img)
        if is_mech:
            return "mechanical", 12

        x_count = _detect_markers(p1, p2, thresh_img, "x")
        if x_count >= 3:
            return "signal", 4

        o_count = _detect_markers(p1, p2, thresh_img, "o")
        if o_count >= 3:
            return "signal", 5

        slash_count = _detect_markers(p1, p2, thresh_img, "slash")
        if slash_count >= 3:
            return "signal", 10

        has_arrow = _detect_arrowhead(p1, p2, thresh_img)
        if has_arrow:
            return "signal", 9

        if dash_type == "dash_dot":
            return "signal", 8
        elif dash_type == "dashed":
            if avg_seg < 8:
                return "signal", 3
            else:
                return "signal", 2
        else:
            return "utility", 0

    # ── Instrument loop grouping ─────────────────────────────────────────

    @staticmethod
    def _parse_tag(text):
        """Extract (instrument_type, loop_number) from a tag or class name."""
        m = _INSTRUMENT_TAG_RE.search(text)
        if m:
            return m.group("type"), int(m.group("loop"))
        return None, None

    @staticmethod
    def _is_instrument_class(name):
        """Check if a class name looks like an instrument."""
        low = name.lower()
        return any(kw in low for kw in _INSTRUMENT_KEYWORDS)

    @staticmethod
    def group_instrument_loops(nodes, typed_lines, image_shape=None):
        """Group instrument symbols into loops.

        Uses two strategies:
        1. Tag-based: parse instrument tag numbers (e.g. LIC-101 → loop 101)
        2. Proximity-based: instruments connected via signal-lines within
           a spatial cluster form a loop.

        Returns dict mapping loop_id → list of node ids.
        """
        loops = defaultdict(list)
        assignments = {}  # node_id → loop_id

        # ── Stage 1: tag-based grouping ───────────────────────────────
        for node in nodes:
            types = [node.get("type", ""), node.get("type_key", ""),
                     node.get("fine_class", ""), node.get("Labels", "")]
            inst_type = loop_num = None
            for t in types:
                if t and t != "N/A":
                    inst_type, loop_num = TopologyEngine._parse_tag(t)
                    if loop_num is not None:
                        break

            # Fallback: check if class name implies instrument
            if loop_num is None:
                name = node.get("type", "")
                fine = node.get("fine_class", "")
                if TopologyEngine._is_instrument_class(name) or \
                   TopologyEngine._is_instrument_class(fine):
                    # Mark as ungrouped instrument (loop assigned later)
                    node["is_instrument"] = True
                continue

            lid = f"loop_{loop_num}"
            assignments[node["id"]] = lid
            loops[lid].append(node["id"])
            node["loop_id"] = lid
            node["is_instrument"] = True

        # ── Stage 2: proximity-based grouping for unassigned instruments ──
        unassigned = [n for n in nodes
                      if n.get("is_instrument") and "loop_id" not in n]

        if unassigned and typed_lines:
            # Build signal-line adjacency: nodes connected via signal lines
            signal_edges = []
            for p1, p2, lt, st in typed_lines:
                if lt != "signal":
                    continue
                # Find nodes near each endpoint
                near_start = [n["id"] for n in nodes
                              if TopologyEngine._dist_to_bbox(p1, n.get("coordinates", [0,0,0,0])) < 30]
                near_end = [n["id"] for n in nodes
                            if TopologyEngine._dist_to_bbox(p2, n.get("coordinates", [0,0,0,0])) < 30]
                for s in near_start:
                    for e in near_end:
                        if s != e:
                            signal_edges.append((s, e))

            # BFS clusters on signal edges
            adj = defaultdict(set)
            for s, e in signal_edges:
                adj[s].add(e)
                adj[e].add(s)

            visited = set()
            cluster_id = 0
            for node in unassigned:
                nid = node["id"]
                if nid in visited:
                    continue
                # BFS
                queue = [nid]
                cluster = []
                while queue:
                    cur = queue.pop(0)
                    if cur in visited:
                        continue
                    visited.add(cur)
                    cluster.append(cur)
                    for nb in adj.get(cur, []):
                        if nb not in visited:
                            queue.append(nb)
                if len(cluster) >= 1:
                    lid = f"prox_loop_{cluster_id}"
                    for cid in cluster:
                        assignments[cid] = lid
                        loops[lid].append(cid)
                        for n in nodes:
                            if n["id"] == cid:
                                n["loop_id"] = lid
                    cluster_id += 1

        return dict(loops)

    @staticmethod
    def _line_intersects_box(p1, p2, bbox, margin=5):
        x1, y1, x2, y2 = bbox
        x1 -= margin; y1 -= margin; x2 += margin; y2 += margin
        
        def _point_in_box(px, py):
            return x1 <= px <= x2 and y1 <= py <= y2
        
        if _point_in_box(p1[0], p1[1]) or _point_in_box(p2[0], p2[1]):
            return True
        
        def _line_intersects_edge(lp1, lp2, e1, e2):
            d1x, d1y = lp2[0]-lp1[0], lp2[1]-lp1[1]
            d2x, d2y = e2[0]-e1[0], e2[1]-e1[1]
            cross = d1x*d2y - d1y*d2x
            if abs(cross) < 1e-10:
                return False
            t = ((e1[0]-lp1[0])*d2y - (e1[1]-lp1[1])*d2x) / cross
            u = ((e1[0]-lp1[0])*d1y - (e1[1]-lp1[1])*d1x) / cross
            return 0 <= t <= 1 and 0 <= u <= 1
        
        edges = [
            ((x1,y1),(x2,y1)), ((x2,y1),(x2,y2)),
            ((x2,y2),(x1,y2)), ((x1,y2),(x1,y1))
        ]
        for e1, e2 in edges:
            if _line_intersects_edge(p1, p2, e1, e2):
                return True
        
        return False

    @staticmethod
    def _point_in_box(px, py, bbox):
        x1, y1, x2, y2 = bbox
        return x1 <= px <= x2 and y1 <= py <= y2

    @staticmethod
    def _filter_lines_in_boxes(segments, bboxes):
        filtered = []
        for p1, p2 in segments:
            inside_count = 0
            for bbox in bboxes:
                if TopologyEngine._point_in_box(p1[0], p1[1], bbox) and \
                   TopologyEngine._point_in_box(p2[0], p2[1], bbox):
                    inside_count = 1
                    break
            if inside_count == 0:
                filtered.append((p1, p2))
        return filtered

    @staticmethod
    def infer_connectivity(symbols, lines, threshold=350):
        """Infer symbol connectivity using proximity + line validation.

        Strategy:
        1. For each symbol pair, check if they're within distance threshold
        2. Validate: at least one detected line endpoint must be near both symbols
        3. This gives high precision (line-validated) + high recall (proximity-based)
        """
        if not lines or not symbols:
            return []

        # Build line endpoint index for fast lookup
        line_eps = []
        for p1, p2 in lines:
            line_eps.append(p1)
            line_eps.append(p2)

        def _has_line_near(sym1_bbox, sym2_bbox):
            """Check if any detected line endpoint is near both symbols."""
            s1_cx = (sym1_bbox[0] + sym1_bbox[2]) / 2
            s1_cy = (sym1_bbox[1] + sym1_bbox[3]) / 2
            s2_cx = (sym2_bbox[0] + sym2_bbox[2]) / 2
            s2_cy = (sym2_bbox[1] + sym2_bbox[3]) / 2

            # Check each line's endpoints
            for i in range(0, len(line_eps), 2):
                ep1 = line_eps[i]
                ep2 = line_eps[i + 1] if i + 1 < len(line_eps) else None

                # Line connects near both symbols?
                d1_s1 = np.hypot(ep1[0] - s1_cx, ep1[1] - s1_cy)
                d1_s2 = np.hypot(ep1[0] - s2_cx, ep1[1] - s2_cy)
                d2_s1 = np.hypot(ep2[0] - s1_cx, ep2[1] - s1_cy) if ep2 else 9999
                d2_s2 = np.hypot(ep2[0] - s2_cx, ep2[1] - s2_cy) if ep2 else 9999

                # One endpoint near sym1, other near sym2
                if (d1_s1 < threshold and d2_s2 < threshold) or \
                   (d2_s1 < threshold and d1_s2 < threshold):
                    return True
                # One endpoint near both (same side)
                if min(d1_s1, d2_s1) < threshold and min(d1_s2, d2_s2) < threshold:
                    return True

            return False

        # Compute symbol centers
        sym_centers = {}
        for s in symbols:
            bbox = s['bbox']
            sym_centers[s['id']] = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

        # Find connected pairs
        edges = []
        sym_list = list(sym_centers.keys())
        for i in range(len(sym_list)):
            for j in range(i + 1, len(sym_list)):
                s1, s2 = sym_list[i], sym_list[j]
                c1, c2 = sym_centers[s1], sym_centers[s2]
                dist = np.hypot(c1[0] - c2[0], c1[1] - c2[1])

                if dist < threshold:
                    # Proximity match - check if line exists
                    s1_bbox = next(s['bbox'] for s in symbols if s['id'] == s1)
                    s2_bbox = next(s['bbox'] for s in symbols if s['id'] == s2)
                    if _has_line_near(s1_bbox, s2_bbox):
                        edges.append((s1, s2))

        return edges

    @staticmethod
    def enrich_edges_with_types(edges, typed_lines, symbols):
        if not typed_lines:
            return [(s, t, "solid", 0) if isinstance(e, tuple) else
                    (e.get("source",""), e.get("target",""), "solid", 0)
                    for e in edges for s, t in [e[:2]]]

        result = []
        for edge in edges:
            if isinstance(edge, (tuple, list)):
                s_id, t_id = edge[:2]
            else:
                s_id = edge.get("source", "")
                t_id = edge.get("target", "")

            sym_s = next((n for n in symbols if n["id"] == s_id), None)
            sym_t = next((n for n in symbols if n["id"] == t_id), None)
            if sym_s and sym_t:
                sb = sym_s.get("bbox", sym_s.get("coordinates", [0,0,0,0]))
                tb = sym_t.get("bbox", sym_t.get("coordinates", [0,0,0,0]))
                mx = (sb[0] + sb[2] + tb[0] + tb[2]) / 4
                my = (sb[1] + sb[3] + tb[1] + tb[3]) / 4

                best_type = "solid"
                best_subtype = 0
                best_dist = float("inf")
                for p1, p2, lt, st in typed_lines:
                    lmx = (p1[0] + p2[0]) / 2
                    lmy = (p1[1] + p2[1]) / 2
                    d = math.hypot(lmx - mx, lmy - my)
                    if d < best_dist:
                        best_dist = d
                        best_type = lt
                        best_subtype = st

                if best_dist > 200:
                    s_type = sym_s.get("type", "")
                    if any(kw in s_type.lower() for kw in ("instrument", "indicator",
                           "transmitter", "controller", "gauge", "switch")):
                        best_type = "signal"

                result.append((s_id, t_id, best_type, best_subtype))
            else:
                result.append((s_id, t_id, "solid", 0))

        return result

    @staticmethod
    def _dist_to_bbox(point, bbox):
        px, py = point
        xmin, ymin, xmax, ymax = bbox
        
        dx = max(xmin - px, 0, px - xmax)
        dy = max(ymin - py, 0, py - ymax)
        return math.sqrt(dx*dx + dy*dy)