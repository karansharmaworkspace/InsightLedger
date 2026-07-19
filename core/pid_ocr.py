"""
P&ID OCR: CRAFT detection + TrOCR recognition + adaptive multi-scale screening.
Production module extracted from OCR Engine/pipeline.py.
"""

import os, re, time
import numpy as np
import cv2
import torch

# ── Normalisation ──────────────────────────────────────────────────────

QUOTE_MAP = str.maketrans({
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    "\u201e": '"', "\u201a": "'", "\u00ab": '"', "\u00bb": '"',
})

OCR_FIX = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", ":": "-", ";": "-"})


def norm(t: str) -> str:
    t = t.translate(QUOTE_MAP).translate(OCR_FIX)
    return t.strip(".,;:!?\"'()[]/ \n").lower()


# ── Geometry helpers ───────────────────────────────────────────────────

def _bbox_iou(box_a, box_b):
    ax1 = min(p[0] for p in box_a); ay1 = min(p[1] for p in box_a)
    ax2 = max(p[0] for p in box_a); ay2 = max(p[1] for p in box_a)
    bx1 = min(p[0] for p in box_b); by1 = min(p[1] for p in box_b)
    bx2 = max(p[0] for p in box_b); by2 = max(p[1] for p in box_b)
    xi1, yi1 = max(ax1, bx1), max(ay1, by1)
    xi2, yi2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    u = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / u if u else 0


def _nms_boxes(results, iou_thresh=0.5):
    results = sorted(results, key=lambda x: -x[2])
    kept = []
    for box, text, conf in results:
        if any(_bbox_iou(box, kb) > iou_thresh for kb, _, _ in kept):
            continue
        kept.append((box, text, conf))
    return kept


# ── Tag-pattern filter ─────────────────────────────────────────────────

TAG_PATTERN = re.compile(
    r'^[\d]+[\"\'\-]?[A-Za-z]+[\"\'\-]?\d*$|'
    r'^[A-Za-z]+-\d+$|'
    r'^\d+[A-Za-z]+$|'
    r'^\d+\"\-[A-Za-z]+\-\d+$|'
    r'^\d+\"[xX]\d+\"$|'
    r'^\d+\"$|'
    r'^[A-Za-z]{2,4}$|'
    r'^[A-Za-z]\.[A-Za-z]{2,3}$|'
    r'^\d{2}[A-Za-z]+\d{2}$|'
    r'^\d+/\d+/\d+$|'
    r'^\d+$'
)


def filter_results(results, min_conf=0.1, min_len=1, prefer_tags=True):
    tags, others = [], []
    for box, text, conf in results:
        t = text.strip()
        if len(t) < min_len or conf < min_conf:
            continue
        item = (box, t, conf)
        if prefer_tags and TAG_PATTERN.match(t):
            tags.append(item)
        else:
            others.append(item)
    tags.sort(key=lambda x: -x[2])
    others.sort(key=lambda x: -x[2])
    return tags + others


# ── CRAFT Detector (single pass) ──────────────────────────────────────

class CRAFTDetector:
    """CRAFT detection via EasyOCR with SAHI-style tiling for large images."""

    def __init__(self, gpu=False,
                 text_threshold=0.25, link_threshold=0.1, low_text=0.2,
                 canvas_size=2560, tile_size=1280, tile_overlap=0.2):
        import easyocr
        self.reader = easyocr.Reader(
            ["en"], gpu=gpu,
            model_storage_directory=os.path.expanduser("~/.EasyOCR/model"),
        )
        self.detect_params = dict(
            text_threshold=text_threshold, link_threshold=link_threshold,
            low_text=low_text, paragraph=False, min_size=6,
        )
        self.canvas_size = canvas_size
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap

    def detect(self, img):
        h, w = img.shape[:2]
        if max(h, w) <= self.tile_size:
            return self._detect_single(img, 0, 0)

        step = int(self.tile_size * (1 - self.tile_overlap))
        tiles = []
        for y in range(0, h, step):
            for x in range(0, w, step):
                y2 = min(y + self.tile_size, h)
                x2 = min(x + self.tile_size, w)
                tiles.append((img[y:y2, x:x2], x, y))

        all_boxes = []
        for tile_img, ox, oy in tiles:
            for box, conf in self._detect_single(tile_img, ox, oy):
                all_boxes.append((box, conf))

        return self._nms(all_boxes, iou_thresh=0.3)

    def _detect_single(self, img, ox, oy):
        cs = min(self.canvas_size, max(img.shape[:2]))
        raw = self.reader.readtext(
            img, canvas_size=cs,
            width_ths=0.1, slope_ths=0.2, ycenter_ths=0.1, height_ths=0.1,
            **self.detect_params,
        )
        return [([[p[0]+ox, p[1]+oy] for p in box], conf) for box, text, conf in raw]

    def _nms(self, boxes, iou_thresh=0.3):
        if not boxes:
            return []
        boxes.sort(key=lambda x: -x[1])
        keep = []
        for box, conf in boxes:
            pts = np.array(box, dtype=np.float32).reshape(-1, 2)
            xa, ya = pts[:, 0].min(), pts[:, 1].min()
            xb, yb = pts[:, 0].max(), pts[:, 1].max()
            overlap = False
            for kbox, _ in keep:
                kpts = np.array(kbox, dtype=np.float32).reshape(-1, 2)
                kxa, kya = kpts[:, 0].min(), kpts[:, 1].min()
                kxb, kyb = kpts[:, 0].max(), kpts[:, 1].max()
                ix1 = max(xa, kxa); iy1 = max(ya, kya)
                ix2 = min(xb, kxb); iy2 = min(yb, kyb)
                inter = max(0, ix2-ix1) * max(0, iy2-iy1)
                area1 = (xb-xa)*(yb-ya)
                area2 = (kxb-kxa)*(kyb-kya)
                if area1 + area2 - inter > 0 and inter / (area1 + area2 - inter) > iou_thresh:
                    overlap = True
                    break
            if not overlap:
                keep.append((box, conf))
        return keep


# ── TrOCR Recognizer with Adaptive Multi-Scale Screening ──────────────

_TROCR = None


def _get_trocr():
    global _TROCR
    if _TROCR is None:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        device = "cuda" if torch.cuda.is_available() else "cpu"
        proc = TrOCRProcessor.from_pretrained("microsoft/trocr-small-printed")
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-printed")
        model.eval()
        model.to(device)
        _TROCR = (proc, model, device)
    return _TROCR


def _prepare_crop(crop):
    if len(crop.shape) == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
    elif crop.shape[2] == 4:
        crop = cv2.cvtColor(crop, cv2.COLOR_BGRA2RGB)
    elif crop.shape[2] == 3:
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    return crop


def _trocr_infer(crop_rgb, max_tokens=64):
    proc, model, device = _get_trocr()
    with torch.no_grad():
        px = proc(images=crop_rgb, return_tensors="pt").pixel_values.to(device)
        gen = model.generate(
            px, max_new_tokens=max_tokens,
            output_scores=True, return_dict_in_generate=True,
        )
        text = proc.batch_decode(gen.sequences, skip_special_tokens=True)[0]
        scores = torch.stack(gen.scores, dim=0)
        probs = scores.softmax(-1).max(-1).values
        conf = probs.mean().item()
    return text.strip(), conf


def _make_variants(crop_rgb):
    """Generate resolution and contrast variants for adaptive screening."""
    variants = [(crop_rgb, "orig")]
    h, w = crop_rgb.shape[:2]

    if max(h, w) < 192:
        s2 = cv2.resize(crop_rgb, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        variants.append((s2, "2x"))
    if max(h, w) < 96:
        s3 = cv2.resize(crop_rgb, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        variants.append((s3, "3x"))

    gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
    variants.append((enhanced_rgb, "clahe"))

    return variants


def recognize_adaptive(crop, conf_thresh=0.3, max_tokens=64):
    if crop is None or min(crop.shape[:2]) < 4:
        return ("", 0.0, "skip")

    crop_rgb = _prepare_crop(crop)
    variants = _make_variants(crop_rgb)

    best_text, best_conf, best_var = "", 0.0, "none"
    for img, var_name in variants:
        text, conf = _trocr_infer(img, max_tokens)
        if conf > best_conf:
            best_text, best_conf, best_var = text, conf, var_name
        if conf >= conf_thresh:
            break

    return best_text, best_conf, best_var


# ── Main Pipeline ──────────────────────────────────────────────────────

class TrocrPIDOCR:
    """CRAFT detection + TrOCR recognition + adaptive screening."""

    def __init__(self, gpu=False, adaptive_conf=0.3,
                 text_threshold=0.25, link_threshold=0.1, low_text=0.2):
        self.detector = CRAFTDetector(
            gpu=gpu,
            text_threshold=text_threshold,
            link_threshold=link_threshold,
            low_text=low_text,
        )
        self.adaptive_conf = adaptive_conf
        _get_trocr()

    def run(self, img, conf_thresh=0.2, prefer_tags=True):
        """
        Detect + recognize on a full image (numpy array or path).
        Returns list of (bbox, text, confidence).
        """
        if isinstance(img, str):
            img = cv2.imread(img)
            if img is None:
                raise FileNotFoundError(img)

        t0 = time.time()
        dets = self.detector.detect(img)
        detect_t = time.time() - t0
        recog_t = 0.0

        all_res = []
        for dbox, dconf in dets:
            xs = [p[0] for p in dbox]
            ys = [p[1] for p in dbox]
            cx1, cy1 = max(0, int(min(xs))), max(0, int(min(ys)))
            cx2 = min(img.shape[1], int(max(xs)))
            cy2 = min(img.shape[0], int(max(ys)))
            if cx2 - cx1 < 4 or cy2 - cy1 < 4:
                continue
            pad = 2
            cx1 = max(0, cx1 - pad); cy1 = max(0, cy1 - pad)
            cx2 = min(img.shape[1], cx2 + pad)
            cy2 = min(img.shape[0], cy2 + pad)
            crop = img[cy1:cy2, cx1:cx2]

            tr = time.time()
            text, tconf, _ = recognize_adaptive(crop, conf_thresh=self.adaptive_conf)
            recog_t += time.time() - tr

            if not text:
                continue
            conf = min(dconf, tconf)
            all_res.append((dbox, text, conf))

        dedup = _nms_boxes(all_res, iou_thresh=0.5)
        dedup = [(b, t, c) for b, t, c in dedup if c >= conf_thresh]
        result = filter_results(dedup, min_conf=conf_thresh, prefer_tags=prefer_tags)

        total_t = time.time() - t0
        import sys
        print(f"  OCR: detect={detect_t:.1f}s, recognize={recog_t:.1f}s, total={total_t:.1f}s", file=sys.stderr)
        return result

    def match_to_nodes(self, ocr_results, validated_nodes, max_dist=100):
        """
        Match each OCR result to the nearest symbol node.
        Returns list of (node_id, text, conf).
        """
        matches = []
        for box, text, conf in ocr_results:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)

            best_node, best_dist = None, max_dist
            for node in validated_nodes:
                x1, y1, x2, y2 = node['coordinates']
                ncx = (x1 + x2) / 2
                ncy = (y1 + y2) / 2
                d = ((cx - ncx) ** 2 + (cy - ncy) ** 2) ** 0.5
                if d < best_dist:
                    best_dist = d
                    best_node = node

            if best_node:
                matches.append((best_node['id'], text, conf))
        
        return matches
