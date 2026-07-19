"""Visual RAG: retrieve top-K → filter by family → vote → classify with confidence."""
import os
import numpy as np
import cv2
import torch
import torch.nn.functional as F

COARSE_TO_FAMILY = {
    "Gate_Valve_Vertical": "valve", "Globe_Valve": "valve", "Ball_Valve": "valve",
    "Gate_Valve_Horizontal": "valve", "Butterfly_Valve": "valve", "Plug_Valve": "valve",
    "Check_Valve": "valve", "Control_Valve_Diaphragm": "valve", "Pressure_Relief_Valve": "valve",
    "Angle_Valve": "valve", "Needle_Valve": "valve", "Pinch_Valve": "valve",
    "Diaphragm_Valve": "valve", "Control_Valve_Alternate": "valve",
    "Centrifugal_Pump": "pump", "Rotary_Pump": "pump",
    "Vertical_Vessel": "vessel", "Centrifugal_Fan": "fan",
    "Orifice_Plate": "flow", "Restriction_Orifice": "flow",
    "Heat_Exchanger": "exchanger", "Air_Cooler": "exchanger",
    "Y-Strainer": "strainer", "Motorized_Actuator": "actuator",
    "Glass_Lined_Reactor": "reactor",
    "Status_Indicator": "instrument", "Level_Gauge": "instrument",
}

SYMBOL_FAMILIES = {
    "valve": ["Valve", "Gate", "Globe", "Ball", "Butterfly", "Plug", "Check", "Needle", "Pinch", "Diaphragm", "Angle", "Relief", "Safety"],
    "pump": ["Pump", "pump"],
    "vessel": ["Vessel", "Tank", "Reactor", "Column", "Tower", "Drum"],
    "fan": ["Fan", "Blower", "Compressor"],
    "flow": ["Orifice", "Flowmeter", "Meter", "Nozzle"],
    "exchanger": ["Exchanger", "Cooler", "Heater", "Condenser", "Reboiler"],
    "strainer": ["Strainer", "Filter"],
    "actuator": ["Motor", "Actuator", "Turbine"],
    "reactor": ["Reactor", "Cracker"],
    "instrument": ["Indicator", "Gauge", "Transmitter", "Controller", "Recorder", "Switch", "Alarm"],
}


class VisualRAG:
    def __init__(self, gallery_dir="assets/class_gallery", cache_path="models/dinov2_embeddings.npz"):
        self.gallery_dir = gallery_dir
        self.cache_path = cache_path
        self.model = None
        self.device = "cpu"
        self.class_names = []
        self.embeddings = None

    def load(self):
        if self.model is None:
            self.model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14", pretrained=True)
            self.model.eval()
            self.model.to(self.device)
        if self.embeddings is None:
            self._load_gallery()
        return self

    def _load_gallery(self):
        if os.path.exists(self.cache_path):
            data = np.load(self.cache_path)
            self.class_names = list(data["class_names"])
            self.embeddings = data["embeddings"]
            return
        self.class_names, embs = [], []
        for fname in sorted(os.listdir(self.gallery_dir)):
            if not fname.endswith(".png"):
                continue
            img = cv2.imread(os.path.join(self.gallery_dir, fname))
            if img is None:
                continue
            emb = self._embed(img)
            if emb is not None:
                self.class_names.append(fname[:-4])
                embs.append(emb)
        self.embeddings = np.stack(embs)
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        np.savez(self.cache_path, class_names=np.array(self.class_names), embeddings=self.embeddings)

    def _preprocess(self, img):
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_LINEAR)
        img = img[:, :, ::-1].astype(np.float32) / 255.0
        img = (img - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
        return torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0).to(self.device)

    @torch.no_grad()
    def _embed(self, img):
        if self.model is None:
            return None
        tensor = self._preprocess(img)
        emb = self.model(tensor)
        emb = F.normalize(emb, dim=-1)
        return emb.cpu().numpy().flatten()

    def _get_family_mask(self, coarse_class):
        if not coarse_class or coarse_class not in COARSE_TO_FAMILY:
            return None
        family = COARSE_TO_FAMILY[coarse_class]
        keywords = SYMBOL_FAMILIES.get(family, [])
        if not keywords:
            return None
        mask = np.array([any(kw in name for kw in keywords) for name in self.class_names])
        return mask if mask.any() else None

    def retrieve(self, img, top_k=10, coarse_class=None):
        if self.embeddings is None or len(self.class_names) == 0:
            return []
        emb = self._embed(img)
        if emb is None:
            return []

        sims = self.embeddings @ emb

        family_mask = self._get_family_mask(coarse_class)
        if family_mask is not None:
            filtered_sims = sims.copy()
            filtered_sims[~family_mask] = -1
            top_idx = np.argsort(filtered_sims)[::-1][:top_k]
            used_sims = sims[top_idx]
        else:
            top_idx = np.argsort(sims)[::-1][:top_k]
            used_sims = sims[top_idx]

        return [
            {"class_name": self.class_names[i], "score": float(s), "rank": r + 1}
            for r, (i, s) in enumerate(zip(top_idx, used_sims))
        ]

    def classify(self, img, coarse_class=None, top_k=5, threshold=0.50):
        results = self.retrieve(img, top_k=top_k, coarse_class=coarse_class)
        if not results:
            return {"class_name": coarse_class or "unknown", "confidence": 0.0, "alternatives": [], "ambiguous": False}

        scores = np.array([r["score"] for r in results])
        best = results[0]

        if best["score"] < threshold:
            return {"class_name": coarse_class or "unknown", "confidence": best["score"], "alternatives": results, "ambiguous": False}

        margin = scores[0] - scores[1] if len(scores) > 1 else 1.0
        ambiguous = margin < 0.05

        if ambiguous:
            n_close = sum(1 for s in scores if s > scores[0] - 0.05)
            penalty = 0.1 * (n_close - 1)
            confidence = max(0.0, best["score"] - penalty)
        else:
            confidence = best["score"]

        return {
            "class_name": best["class_name"],
            "confidence": round(confidence, 4),
            "alternatives": results[1:],
            "ambiguous": ambiguous,
        }
