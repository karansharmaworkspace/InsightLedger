from __future__ import annotations

import os
import base64
import json
import hashlib
from typing import Any

from groq import Groq
from PIL import Image
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)


class GroqVisionClient:
    def __init__(self) -> None:
        self.api_key: str | None = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)
        self.model: str | None = os.getenv("VISION_MODEL")
        self.cache: dict[str, str] = {}

    def _get_image_hash(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            small_img = img.convert("L").resize((12, 12), Image.Resampling.LANCZOS)
            data = list(small_img.getdata())
            avg = sum(data) / len(data)
            bits = "".join(['1' if v > avg else '0' for v in data])
            return hashlib.md5(bits.encode()).hexdigest()

    def classify_batch(self, crop_paths: list[str]) -> list[str | None]:
        if not crop_paths: return []
        final_labels = [None] * len(crop_paths)
        to_classify_indices = []
        to_classify_paths = []
        import pytesseract
        unique_to_classify = {}
        path_to_hash = {}
        for i, path in enumerate(crop_paths):
            h = self._get_image_hash(path)
            path_to_hash[path] = h
            if h in self.cache:
                final_labels[i] = self.cache[h]
            else:
                try:
                    text = pytesseract.image_to_string(Image.open(path), config='--psm 10').strip()
                    if text and len(text) < 5:
                        self.cache[h] = "text"
                        final_labels[i] = "text"
                        continue
                except: pass
                if h not in unique_to_classify:
                    unique_to_classify[h] = path
                to_classify_indices.append(i)
                to_classify_paths.append(path)
        if not to_classify_paths: return final_labels
        unique_hashes = list(unique_to_classify.keys())
        unique_paths = [unique_to_classify[h] for h in unique_hashes]
        import math
        batch_size = 25 
        cell_size = 128
        unique_results = {}
        for i in range(0, len(unique_paths), batch_size):
            chunk_paths = unique_paths[i:i + batch_size]
            chunk_hashes = unique_hashes[i:i + batch_size]
            n = len(chunk_paths)
            cols = 5 
            rows = math.ceil(n / cols)
            sheet = Image.new("RGB", (cols * cell_size, rows * cell_size), (255, 255, 255))
            for j, path in enumerate(chunk_paths):
                symbol = Image.open(path).convert("RGB")
                symbol.thumbnail((cell_size-10, cell_size-10))
                r_idx, c_idx = divmod(j, cols)
                sheet.paste(symbol, (c_idx * cell_size + 5, r_idx * cell_size + 5))
            sheet_path = f"output/batch_{i//batch_size}.png"
            sheet.save(sheet_path)
            base64_image = self._encode_and_compress_image(sheet_path)
            prompt = f"Identify the {n} P&ID symbols in this {cols}x{rows} grid (left-to-right, top-to-bottom). Options: [valve, tank, crossing, connector, text, line, general]. Return JSON: {{\"types\": [...]}}"
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                res = json.loads(completion.choices[0].message.content)
                new_labels = res.get("types", [])
                for j, h in enumerate(chunk_hashes):
                    label = new_labels[j] if j < len(new_labels) else "general"
                    self.cache[h] = label
                    unique_results[h] = label
            except Exception:
                for h in chunk_hashes: unique_results[h] = "general"
        for idx in to_classify_indices:
            h = path_to_hash[crop_paths[idx]]
            final_labels[idx] = unique_results.get(h, "general")
        return final_labels

    def _encode_and_compress_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')


class GroqChat:
    def __init__(self) -> None:
        self.api_key: str | None = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)
        self.model: str | None = os.getenv("CHAT_MODEL")
        self.rag: PIDRAG | None = None

    def index_result(self, result_json: dict[str, Any]) -> None:
        from core.pid_rag import PIDRAG
        self.rag = PIDRAG()
        self.rag.index(result_json)

    def ask(self, query: str, context_json: dict[str, Any] | None = None) -> Any:
        if self.rag:
            relevant = self.rag.retrieve(query, top_k=min(len(self.rag.chunks), 100))
            context_str = "\n".join(c["text"] for c in relevant)
            print(f"[RAG] Retrieved {len(relevant)} chunks for: {query[:50]}")
        elif context_json:
            context_str = json.dumps(context_json, indent=2)
            print(f"[CHAT] Using raw JSON context ({len(context_str)} chars)")
        else:
            context_str = "No P&ID diagram loaded yet."

        prompt = (
            f"You are an industrial P&ID analyst. Answer based on the following data:\n\n"
            f"{context_str}\n\n"
            f"User Question: {query}\n\n"
            f"Be precise. Reference specific symbol IDs and classes when possible."
        )
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                stream=True
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None
