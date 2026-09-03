"""Simple on-disk GET cache to respect arXiv/Semantic Scholar rate limits."""
import hashlib
import json
import time

import requests

import config


def _cache_path(url: str, params: dict | None):
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    return config.CACHE_DIR / f"{key}.json"


def cached_get(url: str, params: dict | None = None, headers: dict | None = None,
                timeout: int | None = None) -> requests.Response | None:
    """GET with a 1-day on-disk cache. Returns a requests.Response-like dict wrapper.

    Returns None on network/HTTP failure so callers can degrade gracefully.
    """
    path = _cache_path(url, params)
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age < config.CACHE_TTL_SECONDS:
            return CachedResponse(json.loads(path.read_text()))

    try:
        resp = requests.get(url, params=params, headers=headers,
                             timeout=timeout or config.REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    body = {"status_code": resp.status_code, "text": resp.text}
    path.write_text(json.dumps(body))
    return CachedResponse(body)


class CachedResponse:
    """Minimal stand-in for requests.Response, backed by cached JSON."""

    def __init__(self, body: dict):
        self.status_code = body["status_code"]
        self.text = body["text"]

    def json(self):
        return json.loads(self.text)
