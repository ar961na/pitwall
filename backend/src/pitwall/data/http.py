"""Polite HTTP client: on-disk JSON cache, rate limiting and retry on 429.

Historical F1 data never changes, so once fetched it's cached forever under data/http_cache.
Calls that can change (season calendars, today's session) pass a `ttl_s`.
"""

import hashlib
import json
import logging
import threading
import time
from pathlib import Path

import httpx

from pitwall.config import settings

log = logging.getLogger(__name__)


class CachedClient:
    def __init__(
        self, base_url: str, name: str, min_interval_s: float, user_agent: str = "pitwall"
    ):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = settings.data_dir / "http_cache" / name
        self.min_interval_s = min_interval_s
        self._client = httpx.Client(timeout=60, headers={"User-Agent": user_agent})
        self._lock = threading.Lock()
        self._last_call = 0.0

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{hashlib.sha1(url.encode()).hexdigest()}.json"

    def get(self, path: str, ttl_s: float | None = None, allow_404: bool = False):
        """GET `path` (may include a query string) and return parsed JSON."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        cached = self._cache_path(url)
        if cached.exists() and (ttl_s is None or time.time() - cached.stat().st_mtime < ttl_s):
            return json.loads(cached.read_text())

        for attempt in range(5):
            with self._lock:  # one request at a time, spaced by min_interval_s
                wait = self._last_call + self.min_interval_s - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                try:
                    resp = self._client.get(url)
                except httpx.TransportError as e:  # dropped keep-alive, timeout, ...
                    log.warning("%s on %s, retrying", type(e).__name__, url)
                    self._last_call = time.monotonic()
                    time.sleep(2**attempt)
                    continue
                finally:
                    self._last_call = time.monotonic()
            if resp.status_code == 429:
                backoff = float(resp.headers.get("Retry-After", 2**attempt * 2))
                log.warning("429 from %s, retrying in %.0fs", self.base_url, backoff)
                time.sleep(backoff)
                continue
            if resp.status_code == 404 and allow_404:
                data = None
                break
            resp.raise_for_status()
            data = resp.json()
            break
        else:
            raise RuntimeError(f"Rate-limited too many times: {url}")

        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(data))
        return data
