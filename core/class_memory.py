from __future__ import annotations

import os
import json
import time
import cv2
import numpy as np
from numpy.typing import NDArray
from typing import Any


class ClassMemory:
    def __init__(self, memory_path: str = "models/class_memory.json", gallery_dir: str = "assets/class_gallery") -> None:
        self.memory_path = memory_path
        self.gallery_dir = gallery_dir
        self.data: dict[str, Any] = self._load()
        self._dinov2: Any = None

    def _get_dinov2(self) -> Any:
        if self._dinov2 is None:
            from core.dinov2_embedder import DinoV2Embedder
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._dinov2 = DinoV2Embedder(
                gallery_dir=os.path.join(base, "assets", "class_gallery"),
                cache_path=os.path.join(base, "models", "dinov2_embeddings.npz")
            )
            self._dinov2.load_model()
        return self._dinov2

    def _load(self) -> dict[str, Any]:
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'r') as f:
                return json.load(f)
        return {"classifications": [], "metadata": {"total": 0}}

    def _save(self) -> None:
        self.data["metadata"]["total"] = len(self.data["classifications"])
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        with open(self.memory_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def add_classification(self, crop: NDArray[np.uint8], user_class: str, parent_class: str, coarse_class: str = "", bbox_ratio: float = 1.0) -> str:
        dinov2 = self._get_dinov2()
        embedding = dinov2.extract_embedding(crop)
        emb_hex = ""
        if embedding is not None:
            emb_hex = np.array(embedding, dtype=np.float32).tobytes().hex()

        entry = {
            "id": f"mem_{int(time.time()*1000)}",
            "coarse_class": coarse_class,
            "user_class": user_class,
            "parent_class": parent_class,
            "bbox_ratio": round(bbox_ratio, 3),
            "embedding": emb_hex,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        self.data["classifications"].append(entry)
        self._save()
        return entry["id"]

    def find_match(self, crop: NDArray[np.uint8], coarse_class: str = "", bbox_ratio: float = 1.0, threshold: float = 0.65) -> dict[str, Any] | None:
        if not self.data["classifications"]:
            return None

        dinov2 = self._get_dinov2()
        crop_emb = dinov2.extract_embedding(crop)
        if crop_emb is None:
            return None

        best_match = None
        best_score = 0.0

        for entry in self.data["classifications"]:
            if not entry.get("embedding"):
                continue

            try:
                stored_emb = np.frombuffer(bytes.fromhex(entry["embedding"]), dtype=np.float32)
            except Exception:
                continue

            if len(stored_emb) != len(crop_emb):
                continue

            cos_sim = float(np.dot(crop_emb, stored_emb) / (np.linalg.norm(crop_emb) * np.linalg.norm(stored_emb) + 1e-8))

            score = cos_sim
            if coarse_class and entry["coarse_class"] == coarse_class:
                score += 0.1

            if score > best_score:
                best_score = score
                best_match = entry

        if best_match and best_score >= threshold:
            return {
                "user_class": best_match["user_class"],
                "parent_class": best_match["parent_class"],
                "score": best_score
            }
        return None

    def get_all_entries(self) -> list[dict[str, Any]]:
        return self.data["classifications"]

    def remove_entry(self, entry_id: str) -> None:
        self.data["classifications"] = [
            e for e in self.data["classifications"] if e["id"] != entry_id
        ]
        self._save()

    @staticmethod
    def load_class_hierarchy(json_path: str) -> dict[str, Any]:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data.get("legend_classification", {}).get("classes", {})

    @staticmethod
    def get_gallery_image(class_name: str, gallery_dir: str) -> str | None:
        path = os.path.join(gallery_dir, f"{class_name}.png")
        if os.path.exists(path):
            return path
        return None
