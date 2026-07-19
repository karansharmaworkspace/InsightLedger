"""
P&ID Symbol Detection using YOLO + SAHI
Uses 32classes.pt model for detecting equipment, instruments, and symbols.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Detection:
    bbox: List[float]  # [x1, y1, x2, y2]
    class_id: int
    class_name: str
    confidence: float


# 32 P&ID symbol classes (ISA-5.1 based)
CLASS_NAMES = {
    0: "centrifugal_pump",
    1: "rotary_pump",
    2: "gear_pump",
    3: "diaphragm_pump",
    4: "gate_valve",
    5: "globe_valve",
    6: "ball_valve",
    7: "butterfly_valve",
    8: "check_valve",
    9: "control_valve",
    10: "safety_valve",
    11: "relief_valve",
    12: "vessel",
    13: "tank",
    14: "column",
    15: "reactor",
    16: "heat_exchanger",
    17: "compressor",
    18: "filter",
    19: "strainer",
    20: "mixer",
    21: "motor",
    22: "turbine",
    23: "fan",
    24: "instrument",
    25: "indicator",
    26: "transmitter",
    27: "controller",
    28: "gauge",
    29: "switch",
    30: "sensor",
    31: "flow_meter",
}

# Class to category mapping
CLASS_CATEGORIES = {
    "centrifugal_pump": "equipment",
    "rotary_pump": "equipment",
    "gear_pump": "equipment",
    "diaphragm_pump": "equipment",
    "gate_valve": "valve",
    "globe_valve": "valve",
    "ball_valve": "valve",
    "butterfly_valve": "valve",
    "check_valve": "valve",
    "control_valve": "valve",
    "safety_valve": "valve",
    "relief_valve": "valve",
    "vessel": "equipment",
    "tank": "equipment",
    "column": "equipment",
    "reactor": "equipment",
    "heat_exchanger": "equipment",
    "compressor": "equipment",
    "filter": "equipment",
    "strainer": "equipment",
    "mixer": "equipment",
    "motor": "equipment",
    "turbine": "equipment",
    "fan": "equipment",
    "instrument": "instrument",
    "indicator": "instrument",
    "transmitter": "instrument",
    "controller": "instrument",
    "gauge": "instrument",
    "switch": "instrument",
    "sensor": "instrument",
    "flow_meter": "instrument",
}


class PIDDetector:
    """
    YOLO + SAHI detector for P&ID symbols.

    Uses SAHI (Slicing Aided Hyper Inference) for better small object detection:
    - Splits image into overlapping slices
    - Runs YOLO inference on each slice
    - Merges results with NMS
    """

    def __init__(
        self,
        model_path: str = "models/32classes.pt",
        conf_thresh: float = 0.35,
        iou_thresh: float = 0.45,
        slice_height: int = 640,
        slice_width: int = 640,
        overlap_height_ratio: float = 0.2,
        overlap_width_ratio: float = 0.2,
    ):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.slice_height = slice_height
        self.slice_width = slice_width
        self.overlap_height_ratio = overlap_height_ratio
        self.overlap_width_ratio = overlap_width_ratio

        self._model = None
        self._sahi_model = None

    def _load_model(self):
        """Lazy-load YOLO model."""
        if self._model is not None:
            return

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model not found: {self.model_path}\n"
                "Download 32classes.pt from DPID AI repository."
            )

        from ultralytics import YOLO
        self._model = YOLO(self.model_path)
        print(f"Loaded model: {self.model_path}")

    def _load_sahi_model(self):
        """Lazy-load SAHI wrapper."""
        if self._sahi_model is not None:
            return

        self._load_model()

        try:
            from sahi import AutoDetectionModel
            self._sahi_model = AutoDetectionModel.from_pretrained(
                model_type="ultralytics",
                model_path=self.model_path,
                confidence_threshold=self.conf_thresh,
                device="cpu",  # Use "cuda" if GPU available
            )
            print("Loaded SAHI detection model")
        except ImportError:
            print("SAHI not available, using standard YOLO inference")
            self._sahi_model = None

    def detect(self, image_path: str) -> List[Detection]:
        """
        Detect P&ID symbols in image using SAHI + YOLO.

        Args:
            image_path: Path to P&ID image

        Returns:
            List of Detection objects with bbox, class, confidence
        """
        self._load_sahi_model()

        if self._sahi_model is not None:
            return self._detect_with_sahi(image_path)
        else:
            return self._detect_standard(image_path)

    def _detect_with_sahi(self, image_path: str) -> List[Detection]:
        """Detect using SAHI slicing inference."""
        from sahi import get_sliced_prediction

        result = get_sliced_prediction(
            image_path,
            self._sahi_model,
            slice_height=self.slice_height,
            slice_width=self.slice_width,
            overlap_height_ratio=self.overlap_height_ratio,
            overlap_width_ratio=self.overlap_width_ratio,
            perform_standard_pred=True,
            postprocess_type="NMS",
            postprocess_match_threshold=self.iou_thresh,
            postprocess_match_class_agnostic=False,
            verbose=0,
        )

        detections = []
        for pred in result.object_prediction_list:
            bbox = pred.bbox
            cls_id = pred.category.id
            cls_name = pred.category.name or CLASS_NAMES.get(cls_id, f"class_{cls_id}")

            detections.append(Detection(
                bbox=[bbox.minx, bbox.miny, bbox.maxx, bbox.maxy],
                class_id=cls_id,
                class_name=cls_name,
                confidence=pred.score.value,
            ))

        return detections

    def _detect_standard(self, image_path: str) -> List[Detection]:
        """Standard YOLO inference (no SAHI slicing)."""
        self._load_model()

        results = self._model(image_path, conf=self.conf_thresh, iou=self.iou_thresh)

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue

            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = CLASS_NAMES.get(cls_id, f"class_{cls_id}")

                detections.append(Detection(
                    bbox=xyxy.tolist(),
                    class_id=cls_id,
                    class_name=cls_name,
                    confidence=conf,
                ))

        return detections

    def detect_with_labels(
        self, image_path: str, ocr_results: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect symbols and match with OCR labels.

        Args:
            image_path: Path to P&ID image
            ocr_results: Optional OCR results [(bbox, text, conf), ...]

        Returns:
            List of detected symbols with matched labels
        """
        detections = self.detect(image_path)

        symbols = []
        for i, det in enumerate(detections):
            # Try to match with OCR label
            label = None
            label_conf = 0.0

            if ocr_results:
                det_cx = (det.bbox[0] + det.bbox[2]) / 2
                det_cy = (det.bbox[1] + det.bbox[3]) / 2

                best_dist = 150  # max pixel distance for matching
                for ocr_bbox, ocr_text, ocr_conf in ocr_results:
                    ocr_cx = sum(p[0] for p in ocr_bbox) / len(ocr_bbox)
                    ocr_cy = sum(p[1] for p in ocr_bbox) / len(ocr_bbox)

                    dist = ((det_cx - ocr_cx) ** 2 + (det_cy - ocr_cy) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        label = ocr_text
                        label_conf = ocr_conf

            symbols.append({
                "id": f"det_{i}",
                "tag": label or f"{det.class_name}_{i}",
                "type": det.class_name,
                "category": CLASS_CATEGORIES.get(det.class_name, "unknown"),
                "bbox": [int(x) for x in det.bbox],
                "confidence": det.confidence,
                "label_confidence": label_conf,
            })

        return symbols

    def get_class_info(self) -> Dict[str, Any]:
        """Return class information for the model."""
        return {
            "total_classes": len(CLASS_NAMES),
            "classes": CLASS_NAMES,
            "categories": CLASS_CATEGORIES,
        }
