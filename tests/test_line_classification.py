"""Test line type classification and instrument loop grouping.

Generates synthetic P&ID-like images with process, signal, and utility lines,
then verifies each is classified correctly. Also tests instrument loop grouping.
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from utils.topology_engine import TopologyEngine


def _draw_line(img, p1, p2, thickness=2, color=255, dash=False):
    """Draw a line on the image. If dash=True, draw dashed."""
    if not dash:
        cv2.line(img, p1, p2, color, thickness)
        return

    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    dash_len = 10
    gap_len = 6
    pos = 0
    while pos < length:
        end = min(pos + dash_len, length)
        sx = int(x1 + ux * pos)
        sy = int(y1 + uy * pos)
        ex = int(x1 + ux * end)
        ey = int(y1 + uy * end)
        cv2.line(img, (sx, sy), (ex, ey), color, thickness)
        pos += dash_len + gap_len


def test_line_type_classification():
    """Verify that process, signal, and utility lines are classified correctly."""
    img_size = (300, 600)
    tests = [
        ("process",    (50, 100),  (250, 100), 5,  False, "process"),
        ("process_v2", (50, 120),  (250, 120), 4,  False, "process"),
        ("signal",     (50, 160),  (250, 160), 1,  True,  "signal"),
        ("signal_v2",  (50, 190),  (200, 190), 2,  True,  "signal"),
        ("utility",    (50, 230),  (250, 230), 1,  False, "utility"),
        ("utility_v2", (50, 260),  (200, 260), 2,  False, "utility"),
    ]

    passed = 0
    failed = 0

    for name, p1, p2, thick, dash, expected in tests:
        img = np.zeros(img_size, dtype=np.uint8)
        _draw_line(img, p1, p2, thickness=thick, color=255, dash=dash)

        _th, thresh = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY)
        result = TopologyEngine.classify_line_type(p1, p2, thresh)

        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {name}: expected={expected}, got={result} "
              f"(thick={thick}, dash={dash})")

    return passed, failed


def test_classify_lines():
    """Verify classify_lines returns correctly typed segments."""
    img_size = (300, 300)
    img = np.full(img_size, 255, dtype=np.uint8)  # white background (like scanned P&ID)

    # Draw one of each type (black lines, inverse of test_line_type_classification)
    _draw_line(img, (20, 50),  (280, 50),  4, 0, False)   # process
    _draw_line(img, (20, 100), (280, 100), 1, 0, True)    # signal
    _draw_line(img, (20, 150), (280, 150), 1, 0, False)   # utility

    # Save and re-read as the method does
    test_path = os.path.join(os.path.dirname(__file__), "_test_line_img.png")
    cv2.imwrite(test_path, img)

    segments = [
        ((20, 50),  (280, 50)),    # process
        ((20, 100), (280, 100)),   # signal
        ((20, 150), (280, 150)),   # utility
    ]

    typed = TopologyEngine.classify_lines(segments, test_path)
    os.remove(test_path)

    expected = ["process", "signal", "utility"]
    passed = 0
    failed = 0

    for i, (p1, p2, lt, subtype) in enumerate(typed):
        status = "PASS" if lt == expected[i] else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] segment[{i}]: expected={expected[i]}, got={lt}")

    return passed, failed


def test_instrument_loop_grouping():
    """Verify instrument loop grouping produces correct loop IDs."""
    nodes = [
        {"id": "Level_Transmitter_0",  "type": "Level_Transmitter",
         "type_key": "Level_Transmitter", "coordinates": [10, 10, 30, 30]},
        {"id": "Level_Indicator_1",    "type": "Level_Indicator",
         "type_key": "Level_Indicator",   "coordinates": [50, 10, 70, 30]},
        {"id": "Control_Valve_2",      "type": "Control_Valve",
         "type_key": "Control_Valve",    "coordinates": [100, 10, 120, 30]},
        {"id": "Gate_Valve_3",         "type": "Gate_Valve",
         "type_key": "Gate_Valve",       "coordinates": [200, 10, 220, 30]},
    ]

    typed_lines = [
        ((20, 20), (60, 20), "signal", 2),
        ((60, 20), (110, 20), "signal", 2),
        ((60, 20), (110, 20), "signal", 2),
    ]

    loops = TopologyEngine.group_instrument_loops(nodes, typed_lines)

    passed = 0
    failed = 0

    # Level_Transmitter and Level_Indicator are instruments; Control_Valve and Gate_Valve are not
    instr_nodes = [n for n in nodes if n.get("is_instrument")]
    non_instr = [n for n in nodes if not n.get("is_instrument")]

    if len(instr_nodes) == 2:
        print(f"  [PASS] 2 instrument nodes detected: {[n['type'] for n in instr_nodes]}")
        passed += 1
    else:
        print(f"  [FAIL] expected 2 instrument nodes, got {len(instr_nodes)}")
        failed += 1

    if len(non_instr) == 2 and all(n["type"] in ("Control_Valve", "Gate_Valve") for n in non_instr):
        print(f"  [PASS] Non-instruments correctly classified: {[n['type'] for n in non_instr]}")
        passed += 1
    else:
        print(f"  [FAIL] Non-instruments misclassified, got: {[n['type'] for n in non_instr]}")
        failed += 1

    # The 3 instruments should be grouped (proximity via signal lines)
    grouped = set()
    for n in instr_nodes:
        if "loop_id" in n:
            grouped.add(n["loop_id"])
    if len(grouped) == 1:
        print(f"  [PASS] Instruments grouped into single loop: {grouped}")
        passed += 1
    else:
        print(f"  [FAIL] Expected 1 loop group, got {len(grouped)}: {grouped}")
        failed += 1

    return passed, failed


def test_tag_based_loop_grouping():
    """Verify tag-based loop grouping works (e.g. LIC-101, TI-101)."""
    nodes = [
        {"id": "node_a", "type": "LIC-101", "type_key": "Level_Controller",
         "coordinates": [0, 0, 10, 10]},
        {"id": "node_b", "type": "TI-101", "type_key": "Temp_Indicator",
         "coordinates": [20, 0, 30, 10]},
        {"id": "node_c", "type": "FV-101", "type_key": "Flow_Valve",
         "coordinates": [40, 0, 50, 10]},
        {"id": "node_d", "type": "Pump_101", "type_key": "Centrifugal_Pump",
         "coordinates": [100, 0, 110, 10], "Labels": "P-101"},
    ]

    loops = TopologyEngine.group_instrument_loops(nodes, [])
    passed = 0
    failed = 0

    # LIC-101, TI-101, FV-101 should all be loop_101
    loop_101 = [n for n in nodes if n.get("loop_id") == "loop_101"]
    if len(loop_101) == 3:
        print(f"  [PASS] 3 nodes in loop_101: {[n['id'] for n in loop_101]}")
        passed += 1
    else:
        print(f"  [FAIL] expected 3 nodes in loop_101, got {len(loop_101)}")
        failed += 1

    # Pump_101 should NOT have loop_101 (it's a pump, not instrument)
    pump = next(n for n in nodes if n["id"] == "node_d")
    if not pump.get("is_instrument"):
        print(f"  [PASS] Pump correctly not marked as instrument")
        passed += 1
    else:
        print(f"  [FAIL] Pump incorrectly marked as instrument")
        failed += 1

    return passed, failed


def test_enrich_edges_with_types():
    """Verify edge type enrichment works."""
    symbols = [
        {"id": "sym_a", "type": "Control_Valve", "coordinates": [0, 0, 10, 10]},
        {"id": "sym_b", "type": "Gate_Valve",    "coordinates": [50, 0, 60, 10]},
    ]
    edges = [("sym_a", "sym_b")]
    typed_lines = [((5, 5), (55, 5), "process", 1)]

    result = TopologyEngine.enrich_edges_with_types(edges, typed_lines, symbols)
    passed = 0
    failed = 0

    if len(result) == 1:
        s, t, lt, st = result[0]
        if s == "sym_a" and t == "sym_b" and lt == "process":
            print(f"  [PASS] Edge typed as process")
            passed += 1
        else:
            print(f"  [FAIL] Unexpected result: {result[0]}")
            failed += 1
    else:
        print(f"  [FAIL] Expected 1 enriched edge, got {len(result)}")
        failed += 1

    return passed, failed


def test_re_parse_instrument_tag():
    """Verify ISA-5.1 tag regex."""
    from utils.topology_engine import _INSTRUMENT_TAG_RE
    tests = [
        ("LIC-101", "LIC", 101),
        ("TI-102", "TI", 102),
        ("FIC-103", "FIC", 103),
        ("PDIT-204", "PDIT", 204),
        ("P-101", None, None),  # Just a pump tag, not instrument pattern
        ("Control_Valve", None, None),
    ]
    passed = 0
    failed = 0
    for text, exp_type, exp_num in tests:
        m = _INSTRUMENT_TAG_RE.search(text)
        if exp_type is None:
            if m is None:
                print(f"  [PASS] '{text}' correctly rejected")
                passed += 1
            else:
                print(f"  [FAIL] '{text}' should not match, got {m.group()}")
                failed += 1
        else:
            if m and m.group("type") == exp_type and int(m.group("loop")) == exp_num:
                print(f"  [PASS] '{text}' -> type={exp_type}, loop={exp_num}")
                passed += 1
            else:
                print(f"  [FAIL] '{text}' expected type={exp_type}, loop={exp_num}")
                failed += 1

    return passed, failed


if __name__ == "__main__":
    total_passed = 0
    total_failed = 0

    print("=" * 60)
    print("Line Type Classification Tests")
    print("=" * 60)

    print("\n--- test_line_type_classification ---")
    p, f = test_line_type_classification()
    total_passed += p; total_failed += f

    print("\n--- test_classify_lines ---")
    p, f = test_classify_lines()
    total_passed += p; total_failed += f

    print("\n--- test_enrich_edges_with_types ---")
    p, f = test_enrich_edges_with_types()
    total_passed += p; total_failed += f

    print("\n" + "=" * 60)
    print("Instrument Loop Grouping Tests")
    print("=" * 60)

    print("\n--- test_instrument_loop_grouping ---")
    p, f = test_instrument_loop_grouping()
    total_passed += p; total_failed += f

    print("\n--- test_tag_based_loop_grouping ---")
    p, f = test_tag_based_loop_grouping()
    total_passed += p; total_failed += f

    print("\n--- test_re_parse_instrument_tag ---")
    p, f = test_re_parse_instrument_tag()
    total_passed += p; total_failed += f

    print("\n" + "=" * 60)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    sys.exit(0 if total_failed == 0 else 1)
