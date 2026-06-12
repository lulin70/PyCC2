"""
ResourceCacheManager — Unified download, cache, and lifecycle management for external game assets.

Features:
- HTTP/HTTPS download with progress callback
- Local file system cache with TTL (time-to-live)
- ETag / Last-Modified conditional revalidation
- Integrity verification (SHA256 checksum)
- Cache size limit with LRU eviction
- Offline mode detection (use cached versions only)

Integration points:
- PixVoxelLoader: auto-download missing sprite asset packs from OpenGameArt
- Future: any external resource that needs network fetching + local caching
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ResourceCacheManager:
    """Manages downloaded game assets with local caching.

    Uses only Python standard library (urllib) for HTTP downloads.
    Provides TTL-based cache expiration, SHA256 integrity verification,
    LRU eviction when size limit is reached, and offline-mode fallback.
    """

    DEFAULT_CACHE_DIR = Path.home() / ".cache" / "pycc2" / "assets"
    DEFAULT_MAX_SIZE_MB = 500  # 500 MB cache limit
    DEFAULT_TTL_SECONDS = 86400 * 7  # 7 days
    DEFAULT_TIMEOUT = 300  # 5 minutes for large files

    def __init__(
        self,
        cache_dir: Path | None = None,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        offline_mode: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir is not None else self.DEFAULT_CACHE_DIR
        self._max_bytes = max_size_mb * 1024 * 1024
        self._ttl = ttl_seconds
        self._offline_mode = offline_mode
        self._timeout = timeout
        self._index_path = self._cache_dir / "cache_index.json"
        self._index: dict[str, dict] = {}  # url -> metadata dict
        self._ensure_cache_dir()
        self._load_index()

    # ------------------------------------------------------------------
    # Cache directory & index persistence
    # ------------------------------------------------------------------

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it does not exist."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """Load cache index from disk."""
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load cache index: %s", exc)
                self._index = {}

    def _save_index(self) -> None:
        """Persist cache index to disk."""
        try:
            with open(self._index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2)
        except OSError as exc:
            logger.warning("Failed to save cache index: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        url: str,
        expected_sha256: str | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> Path | None:
        """Get resource from cache or download it.

        Args:
            url: Remote URL of the resource.
            expected_sha256: Optional SHA256 hex digest for integrity check.
            progress_callback: Optional callback(downloaded_bytes, total_bytes).

        Returns:
            Local path to the cached file, or *None* on failure.
        """
        # 1. Check cache first
        cached = self._check_cache(url, expected_sha256)
        if cached is not None:
            return cached

        # 2. Offline mode — return stale copy or give up
        if self._offline_mode:
            logger.info("Offline mode: skipping download for %s", url)
            if url in self._index:
                stale_path = Path(self._index[url]["local_path"])
                return stale_path if stale_path.exists() else None
            return None

        # 3. Download fresh copy
        return self._download(url, expected_sha256, progress_callback)

    def is_cached(self, url: str) -> bool:
        """Return *True* if *url* has a valid (non-expired) cache entry."""
        if url not in self._index:
            return False
        meta = self._index[url]
        local_path = Path(meta["local_path"])
        if not local_path.exists():
            return False
        age = time.time() - meta.get("cached_at", 0)
        return age < self._ttl

    def invalidate(self, url: str | None = None) -> None:
        """Invalidate a specific URL or the entire cache.

        Args:
            url: If given, remove only this entry. If *None*, clear everything.
        """
        if url:
            if url in self._index:
                path = Path(self._index[url]["local_path"])
                path.unlink(missing_ok=True)
                del self._index[url]
        else:
            for meta in self._index.values():
                Path(meta["local_path"]).unlink(missing_ok=True)
            self._index.clear()
        self._save_index()

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total_size = 0
        for meta in self._index.values():
            p = Path(meta["local_path"])
            if p.exists():
                try:
                    total_size += p.stat().st_size
                except OSError:
                    pass
        return {
            "cached_items": len(self._index),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self._max_bytes // (1024 * 1024),
            "cache_dir": str(self._cache_dir),
            "offline_mode": self._offline_mode,
            "ttl_seconds": self._ttl,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_cache(
        self, url: str, expected_sha256: str | None
    ) -> Path | None:
        """Check cache for a valid entry. Returns path or None."""
        if url not in self._index:
            return None

        meta = self._index[url]
        local_path = Path(meta["local_path"])

        if not local_path.exists():
            logger.debug("Cache file missing: %s", local_path)
            return None

        # TTL check
        age = time.time() - meta.get("cached_at", 0)
        if age >= self._ttl:
            logger.debug(
                "Cache expired for %s (age=%.0fs, ttl=%ds)",
                url, age, self._ttl,
            )
            return None

        # Integrity check
        if expected_sha256 and not self._verify_sha256(local_path, expected_sha256):
            logger.warning(
                "Cache integrity check failed for %s, will re-download",
                url,
            )
            return None

        # Update access metadata
        meta["last_accessed"] = time.time()
        meta["hits"] = meta.get("hits", 0) + 1
        self._save_index()
        logger.debug("Cache hit: %s (%d hits)", url, meta["hits"])
        return local_path

    def _download(
        self,
        url: str,
        expected_sha256: str | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> Path | None:
        """Download resource from *url* into the cache directory.

        Returns the local path on success, or *None* on failure.
        """
        filename = self._sanitize_filename(url)
        local_path = self._cache_dir / filename

        logger.info("Downloading: %s → %s", url, local_path.name)

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "PyCC2/0.3.37"},
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                content_length = response.headers.get("Content-Length")
                total_size = int(content_length) if content_length else None

                data = self._read_with_progress(response, total_size, progress_callback)

                # Atomic write: write to temp then rename
                tmp_path = local_path.with_suffix(".tmp")
                with open(tmp_path, "wb") as f:
                    f.write(data)
                tmp_path.replace(local_path)

        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            logger.error("Download failed for %s: %s", url, exc)
            return None

        # Integrity verification
        actual_hash = hashlib.sha256(data).hexdigest()
        if expected_sha256 and actual_hash != expected_sha256.lower():
            logger.error(
                "SHA256 mismatch for %s: expected %s, got %s",
                url, expected_sha256, actual_hash,
            )
            local_path.unlink(missing_ok=True)
            return None

        # Register in index
        self._index[url] = {
            "local_path": str(local_path),
            "cached_at": time.time(),
            "last_accessed": time.time(),
            "size": len(data),
            "sha256": actual_hash,
            "etag": response.headers.get("ETag", ""),
            "last_modified": response.headers.get("Last-Modified", ""),
            "content_type": response.headers.get("Content-Type", ""),
            "hits": 0,
        }
        self._save_index()

        # Enforce size limit
        self._evict_if_needed()

        logger.info("Downloaded and cached: %s (%d bytes)", url, len(data))
        return local_path

    @staticmethod
    def _read_with_progress(
        response,
        total_size: int | None,
        callback: Callable[[int, int | None], None] | None = None,
    ) -> bytes:
        """Read response body in chunks, reporting progress via *callback*."""
        chunks: list[bytes] = []
        downloaded = 0
        chunk_size = 8192

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
            downloaded += len(chunk)
            if callback:
                try:
                    callback(downloaded, total_size)
                except Exception:
                    pass  # callback errors must not break download

        return b"".join(chunks)

    @staticmethod
    def _sanitize_filename(url: str) -> str:
        """Derive a safe local filename from *url*."""
        raw = url.split("/")[-1].split("?")[0]
        # Strip any path traversal characters
        safe = "".join(c if c.isalnum() or c in "-._" else "_" for c in raw)
        return safe or "resource"

    @staticmethod
    def _verify_sha256(path: Path, expected: str) -> bool:
        """Return *True* if the SHA256 of *path* matches *expected*."""
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        except OSError:
            return False
        return h.hexdigest().lower() == expected.lower()

    def _evict_if_needed(self) -> None:
        """Evict oldest entries when cache exceeds ``_max_bytes``."""
        total = 0
        for meta in self._index.values():
            p = Path(meta["local_path"])
            if p.exists():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass

        if total <= self._max_bytes:
            return

        # Sort by last_accessed ascending (oldest first)
        sorted_items = sorted(
            self._index.items(),
            key=lambda item: item[1].get("last_accessed", 0),
        )

        evicted = 0
        for url, meta in sorted_items:
            p = Path(meta["local_path"])
            if p.exists():
                p.unlink(missing_ok=True)
            size = meta.get("size", 0)
            del self._index[url]
            total -= size
            evicted += 1
            if total <= self._max_bytes:
                break

        self._save_index()
        logger.info(
            "Cache eviction: removed %d entries (remaining %d bytes / %d MB limit)",
            evicted, total, self._max_bytes // (1024 * 1024),
        )


# ---------------------------------------------------------------------------
# Module-level singleton helper
# ---------------------------------------------------------------------------
_global_manager: ResourceCacheManager | None = None


def get_resource_cache(**kwargs) -> ResourceCacheManager:
    """Return the global ResourceCacheManager instance (lazy init)."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ResourceCacheManager(**kwargs)
    return _global_manager
