"""
Performance Optimization - Query caching and async processing
"""
import time
import hashlib
import json
from typing import Optional, Any, Callable
from collections import OrderedDict
from functools import wraps
from threading import Lock


class QueryCache:
    """LRU cache for query results with TTL"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: OrderedDict[str, dict] = OrderedDict()
        self.lock = Lock()

    def _make_key(self, query: str, params: Optional[dict] = None) -> str:
        raw = json.dumps({"q": query, "p": params or {}}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, query: str, params: Optional[dict] = None) -> Optional[Any]:
        key = self._make_key(query, params)
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry["ts"] < self.ttl:
                    self.cache.move_to_end(key)
                    return entry["result"]
                del self.cache[key]
        return None

    def set(self, query: str, result: Any, params: Optional[dict] = None):
        key = self._make_key(query, params)
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = {"result": result, "ts": time.time()}
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def invalidate(self, pattern: Optional[str] = None):
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                keys_to_del = [k for k in self.cache if pattern in k]
                for k in keys_to_del:
                    del self.cache[k]

    def stats(self) -> dict:
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
            }


def cached_query(cache: QueryCache, ttl: int = 300):
    """Decorator to cache query results"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            query_key = str(args) + str(kwargs)
            result = cache.get(query_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(query_key, result)
            return result
        return wrapper
    return decorator


class AsyncProcessor:
    """Simple async task queue for background processing"""

    def __init__(self):
        self.tasks: list[dict] = []
        self.completed: list[dict] = []
        self.lock = Lock()

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        with self.lock:
            self.tasks.append({
                "id": task_id,
                "func": func,
                "args": args,
                "kwargs": kwargs,
                "status": "pending",
                "submitted_at": time.time(),
            })
        return task_id

    def get_status(self, task_id: str) -> Optional[dict]:
        with self.lock:
            for task in self.tasks:
                if task["id"] == task_id:
                    return {"id": task["id"], "status": task["status"]}
            for task in self.completed:
                if task["id"] == task_id:
                    return {"id": task["id"], "status": "completed"}
        return None


# Global instances
_query_cache = QueryCache(max_size=200, ttl_seconds=600)
_async_processor = AsyncProcessor()


def get_query_cache() -> QueryCache:
    return _query_cache


def get_async_processor() -> AsyncProcessor:
    return _async_processor
