"""Lightweight dynamic translation using deep-translator (Google Translate backend).

Protects numbers and the software name 'DOCOKF' / 'InsightLedger' from translation.
Caches results aggressively and uses batch API calls to avoid rate limits.

Persistent disk cache: translations are saved to a JSON file so each language
pair is only fetched from Google once — even across app restarts.
"""

import json
import os
import re
import time
import random
import threading
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# patterns to protect from translation
# ---------------------------------------------------------------------------
_PROTECTED_WORDS = ["DOCOKF", "InsightLedger"]
_NUM_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)+\b|\b\d+\b")
_PH = "_PH_"  # placeholder prefix — Google Translate preserves it

# Where the persistent cache lives
_CACHE_DIR = Path.home() / ".dpid_ai"
_CACHE_FILE = _CACHE_DIR / "translation_cache.json"


def _protect(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replace protected words and numbers with placeholders; return (masked, replacements)."""
    replacements: list[tuple[str, str]] = []
    masked = text

    def _save_num(m: re.Match) -> str:
        tok = m.group(0)
        ph = f"{_PH}{len(replacements)}_N"
        replacements.append((ph, tok))
        return ph

    masked = _NUM_PATTERN.sub(_save_num, masked)

    for word in _PROTECTED_WORDS:
        while word in masked:
            ph = f"{_PH}{len(replacements)}_W"
            replacements.append((ph, word))
            masked = masked.replace(word, ph, 1)

    return masked, replacements


def _restore(masked: str, replacements: list[tuple[str, str]]) -> str:
    """Put protected tokens back after translation."""
    result = masked
    for ph, original in replacements:
        result = result.replace(ph, original)
    return result


# ---------------------------------------------------------------------------
# TranslationService
# ---------------------------------------------------------------------------
class TranslationService:
    """Thread-safe translation service with in-memory + disk cache.

    Uses Google Translate (free, no API key).  Falls back to original text on
    any failure so the application never crashes due to a translation error.

    Disk cache: saves every translation to ~/.dpid_ai/translation_cache.json.
    On next launch everything is loaded instantly — Google is only called once
    per (text, language) pair ever.
    """

    _BATCH_SIZE = 100
    _MAX_RETRIES = 5
    _KEY_SEP = "||"

    def __init__(self):
        self._cache: dict[tuple[str, str], str] = {}
        self._lock = threading.Lock()
        self._rate_limit_lock = threading.Lock()
        self._last_request_time = 0.0
        self._min_interval = 0.05  # 50ms between batch requests
        self._dirty = False  # any unsaved changes?
        self._load_disk_cache()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def translate(self, text: str, target: str, source: str = "en") -> str:
        """Translate *text* from *source* language to *target*.

        Preserves numbers and protected software names.
        Returns original text on error.
        """
        if not text or not text.strip():
            return text
        if target == source:
            return text

        key = (text, target)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        masked, replacements = _protect(text)

        try:
            translated = self._call_api(masked, target, source)
            translated = translated or masked
        except Exception:
            translated = masked

        result = _restore(translated, replacements)

        with self._lock:
            if key not in self._cache:
                self._cache[key] = result
                self._dirty = True

        return result

    def translate_batch(
        self, texts: list[str], target: str, source: str = "en"
    ) -> list[str]:
        """Translate multiple texts in batched API calls.

        Only uncached texts are sent to the API.  Cached texts are returned
        immediately from the cache.  New translations are saved to disk after
        the API call.
        """
        if not texts:
            return []

        # separate cached vs uncached
        indices: list[int] = []
        uncached_texts: list[str] = []
        result_map: dict[int, str] = {}

        for i, t in enumerate(texts):
            if not t or not t.strip() or target == source:
                result_map[i] = t
                continue
            key = (t, target)
            cached = self._cache.get(key)
            if cached is not None:
                result_map[i] = cached
            else:
                indices.append(i)
                uncached_texts.append(t)

        if not uncached_texts:
            return [result_map[i] for i in range(len(texts))]

        # protect all texts
        protected: list[tuple[str, list[tuple[str, str]]]] = [
            _protect(t) for t in uncached_texts
        ]
        masked_list = [p[0] for p in protected]

        # call API in batches with retry
        translated_list = self._call_api_batch(masked_list, target, source)

        new_entries: dict[tuple[str, str], str] = {}
        results: list[str] = []
        for i, (masked_text, replacements) in enumerate(protected):
            translated = translated_list[i] if i < len(translated_list) else masked_text
            result = _restore(translated or masked_text, replacements)
            key = (uncached_texts[i], target)
            new_entries[key] = result
            results.append(result)

        # batch-insert into cache and save to disk
        with self._lock:
            for k, v in new_entries.items():
                if k not in self._cache:
                    self._cache[k] = v
                    self._dirty = True
            if self._dirty:
                self._save_disk_cache()

        # merge back in original order
        final: list[str] = []
        for i in range(len(texts)):
            if i in result_map:
                final.append(result_map[i])
            else:
                idx = indices.index(i)
                final.append(results[idx])

        return final

    def prewarm(
        self, texts: list[str], target: str, source: str = "en"
    ) -> None:
        """Pre-warm the cache by translating all texts in batch.

        Call this once on language change to avoid per-item delays later.
        """
        self.translate_batch(texts, target, source)

    def clear_cache(self) -> None:
        """Clear the in-memory and disk cache."""
        with self._lock:
            self._cache.clear()
            self._dirty = True
            self._save_disk_cache()

    @lru_cache(maxsize=256)
    def language_name(self, code: str) -> str:
        """Return the English name of a language code (e.g., 'de' -> 'German')."""
        from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES

        reverse = {v: k for k, v in GOOGLE_LANGUAGES_TO_CODES.items()}
        return reverse.get(code, code)

    # ------------------------------------------------------------------
    # disk cache
    # ------------------------------------------------------------------
    def _cache_key(self, text: str, target: str, source: str = "en") -> str:
        """Serialize a (source, target, text) triple to a JSON-safe string key."""
        return f"{source}{self._KEY_SEP}{target}{self._KEY_SEP}{text}"

    def _load_disk_cache(self) -> None:
        """Load translations from the disk cache file on startup."""
        if not _CACHE_FILE.exists():
            return
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                raw: dict[str, str] = json.load(f)
            loaded = 0
            for flat_key, translation in raw.items():
                parts = flat_key.split(self._KEY_SEP, 2)
                if len(parts) == 3:
                    src, tgt, text = parts
                    self._cache[(text, tgt)] = translation
                    loaded += 1
        except Exception:
            # corrupt cache file — ignore, will be rebuilt
            pass

    def _save_disk_cache(self) -> None:
        """Write in-memory cache to disk as JSON."""
        if not self._dirty:
            return
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            # Flatten tuple keys to JSON-safe string keys
            raw: dict[str, str] = {}
            for (text, tgt), translation in self._cache.items():
                flat = self._cache_key(text, tgt)
                raw[flat] = translation
            with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=1)
            self._dirty = False
        except Exception:
            # best-effort — next save will retry
            pass

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------
    def _call_api(self, text: str, target: str, source: str) -> str:
        """Single-text API call with rate-limit throttling and retry."""
        from deep_translator import GoogleTranslator

        with self._rate_limit_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

        last_err: Exception | None = None
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                result: str = GoogleTranslator(
                    source=source, target=target
                ).translate(text)
                return result or text
            except Exception as e:
                last_err = e
                if "429" in str(e) or "Too Many Requests" in str(e):
                    delay = 2**attempt + random.uniform(0, 0.5)
                    time.sleep(delay)
                else:
                    break
        raise last_err  # type: ignore[misc]

    def _call_api_batch(
        self, texts: list[str], target: str, source: str
    ) -> list[str]:
        """Batch API call splitting into chunks, with rate-limit throttling."""
        from deep_translator import GoogleTranslator

        results: list[str] = []
        for chunk_start in range(0, len(texts), self._BATCH_SIZE):
            chunk = texts[chunk_start : chunk_start + self._BATCH_SIZE]

            with self._rate_limit_lock:
                elapsed = time.time() - self._last_request_time
                if elapsed < self._min_interval:
                    time.sleep(self._min_interval - elapsed)
                self._last_request_time = time.time()

            last_err: Exception | None = None
            for attempt in range(1, self._MAX_RETRIES + 1):
                try:
                    chunk_results: list[str] = GoogleTranslator(
                        source=source, target=target
                    ).translate_batch(chunk)
                    results.extend(
                        r if r else chunk[i] for i, r in enumerate(chunk_results)
                    )
                    break
                except Exception as e:
                    last_err = e
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        delay = 2**attempt + random.uniform(0, 0.5)
                        time.sleep(delay)
                    else:
                        results.extend(chunk)
                        break
            else:
                results.extend(chunk)

        return results


# ---------------------------------------------------------------------------
# module-level singleton
# ---------------------------------------------------------------------------
_translator = TranslationService()


def get_translator() -> TranslationService:
    return _translator
