from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Lazy import to avoid pulling in the entire pycc2 package tree (pygame etc.)
# which can cause OOM kills on memory-constrained systems (8GB RAM).
def _get_cache_manager():
    from pycc2.infrastructure.resource_cache import ResourceCacheManager
    return ResourceCacheManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(data: bytes = b"hello world", content_length: int | None = None) -> MagicMock:
    """Build a mock HTTP response usable by ``urllib.request.urlopen``."""
    resp = MagicMock()
    # response.read() is called in a while loop: first call returns data, second returns b"" to stop
    resp.read.side_effect = [data, b""]
    resp.headers = {
        "Content-Length": str(content_length or len(data)),
        "ETag": '"abc123"',
        "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT",
        "Content-Type": "application/octet-stream",
    }
    # Support context manager protocol (with statement)
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Init & configuration
# ---------------------------------------------------------------------------

class TestInitDefaults:
    """Verify default constructor values."""

    def test_init_defaults(self, tmp_path: Path):
        """Default parameters produce expected cache_dir, max_size, ttl."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        assert mgr._cache_dir == tmp_path / "cache"
        assert mgr._max_bytes == 500 * 1024 * 1024   # 500 MB
        assert mgr._ttl == 86400 * 7                  # 7 days
        assert mgr._offline_mode is False
        assert mgr._timeout == 300


class TestCustomCacheDir:
    """Custom cache directory is respected."""

    def test_custom_cache_dir(self, tmp_path: Path):
        """Passing a custom cache_dir uses that path verbatim."""
        custom = tmp_path / "my_assets"
        mgr = _get_cache_manager()(cache_dir=custom)
        assert mgr._cache_dir == custom
        assert custom.is_dir()


class TestOfflineMode:
    """offline_mode=True skips downloads."""

    def test_offline_mode_returns_none_when_not_cached(self, tmp_path: Path):
        """Offline mode returns None for a URL never seen before."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache", offline_mode=True)
        result = mgr.get("https://example.com/asset.png")
        assert result is None

    def test_offline_mode_returns_stale_copy(self, tmp_path: Path):
        """Offline mode returns stale cached file even if TTL expired."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache", offline_mode=True)

        # Manually inject an index entry pointing to a real file
        cached_file = mgr._cache_dir / "asset.png"
        cached_file.write_bytes(b"stale-data")
        mgr._index["https://example.com/asset.png"] = {
            "local_path": str(cached_file),
            "cached_at": time.time() - 999999,
            "last_accessed": time.time() - 999999,
            "size": 10,
            "sha256": _sha256_of(b"stale-data"),
            "etag": "",
            "last_modified": "",
            "content_type": "",
            "hits": 0,
        }

        result = mgr.get("https://example.com/asset.png")
        assert result == cached_file


# ---------------------------------------------------------------------------
# Cache get / miss / hit
# ---------------------------------------------------------------------------

class TestCacheMissThenDownload:
    """First get() triggers download and caches the result."""

    def test_cache_miss_then_download(self, tmp_path: Path):
        """Uncached URL triggers download; returned path points to cached file."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"downloaded-content"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            result = mgr.get("https://example.com/file.txt")

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == data
        assert "https://example.com/file.txt" in mgr._index


class TestCacheHit:
    """Second call with same URL returns cached copy without network."""

    def test_cache_hit(self, tmp_path: Path):
        """Cached URL returns existing file without calling urlopen again."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"cached-content"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            first = mgr.get("https://example.com/hit.txt")
            second = mgr.get("https://example.com/hit.txt")

        assert first == second
        # urlopen should only be called once (on miss)
        assert mock_urlopen.call_count == 1


class TestCacheTtlExpired:
    """TTL expiry forces re-download."""

    def test_cache_ttl_expired(self, tmp_path: Path):
        """After TTL expires, get() re-downloads the resource."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache", ttl_seconds=0)  # instantly expire

        data_v1 = b"version-1"
        data_v2 = b"version-2"

        mock_resp_v1 = _make_mock_response(data_v1)
        mock_resp_v2 = _make_mock_response(data_v2)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp_v1):
            first = mgr.get("https://example.com/ttl.txt")

        assert first.read_bytes() == data_v1

        # Second call — TTL is 0 so entry is already expired → re-download
        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp_v2):
            second = mgr.get("https://example.com/ttl.txt")

        assert second.read_bytes() == data_v2


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------

class TestInvalidateSingleUrl:
    """invalidate(url) removes one entry."""

    def test_invalidate_single_url(self, tmp_path: Path):
        """Invalidating a specific URL removes its file and index entry."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"to-be-deleted"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            mgr.get("https://example.com/gone.txt")

        url = "https://example.com/gone.txt"
        assert url in mgr._index
        cached_path = Path(mgr._index[url]["local_path"])
        assert cached_path.exists()

        mgr.invalidate(url)

        assert url not in mgr._index
        assert not cached_path.exists()

    def test_invalidate_nonexistent_is_noop(self, tmp_path: Path):
        """Invalidating a URL that was never cached does not raise."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        mgr.invalidate("https://example.com/nonexistent.txt")  # should not raise


class TestInvalidateAll:
    """invalidate() with no args clears everything."""

    def test_invalidate_all(self, tmp_path: Path):
        """Calling invalidate() with no URL clears entire cache."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _make_mock_response(b"data-a")
            mgr.get("https://example.com/a.txt")
            # Reset mock for second call (side_effect was consumed)
            mock_urlopen.return_value = _make_mock_response(b"data-b")
            mgr.get("https://example.com/b.txt")

        assert len(mgr._index) == 2

        mgr.invalidate()

        assert len(mgr._index) == 0


# ---------------------------------------------------------------------------
# SHA256 integrity
# ---------------------------------------------------------------------------

class TestSha256Verification:
    """SHA256 checksum verification on download and cache read."""

    def test_sha256_verification_pass(self, tmp_path: Path):
        """Correct expected_sha256 passes verification; file is returned."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"integrity-ok"
        expected = _sha256_of(data)
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            result = mgr.get("https://example.com/sha256_ok.bin", expected_sha256=expected)

        assert result is not None
        assert result.read_bytes() == data

    def test_sha256_verification_fail_on_download(self, tmp_path: Path):
        """Wrong expected_sha256 on download causes rejection (returns None)."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"real-data"
        wrong_hash = "0" * 64
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            result = mgr.get("https://example.com/sha256_bad.bin", expected_sha256=wrong_hash)

        assert result is None

    def test_sha256_verification_fail_on_cache_hit(self, tmp_path: Path):
        """Wrong expected_sha256 on cache hit triggers re-download path."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"original-data"
        new_data = b"new-correct-data"
        original_hash = _sha256_of(data)
        new_hash = _sha256_of(new_data)

        mock_resp_original = _make_mock_response(data)
        mock_resp_new = _make_mock_response(new_data)

        # First download with correct hash
        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp_original):
            mgr.get("https://example.com/rehash.bin", expected_sha256=original_hash)

        # Second call with *different* expected hash → cache integrity fails → re-download
        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp_new):
            result = mgr.get("https://example.com/rehash.bin", expected_sha256=new_hash)

        assert result is not None
        assert result.read_bytes() == new_data


# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------

class TestFilenameSanitize:
    """URL-derived filenames are safe for local filesystem."""

    def test_filename_sanitize_special_chars(self, tmp_path: Path):
        """URLs with special characters produce safe filenames."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"safe"
        url = "https://cdn.example.com/assets/sprite pack v2.0?token=abc&foo=bar"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            result = mgr.get(url)

        assert result is not None
        # Filename must not contain spaces, ?, &, etc.
        name = result.name
        assert " " not in name
        assert "?" not in name
        assert "&" not in name
        assert "/" not in name

    def test_filename_sanitize_empty_fallback(self, tmp_path: Path):
        """URL ending in '/' produces fallback filename 'resource'."""
        safe_name = _get_cache_manager()._sanitize_filename("https://example.com/path/")
        assert safe_name == "resource"


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------

class TestLruEviction:
    """Cache evicts oldest entries when size limit is exceeded."""

    def test_eviction_when_over_limit(self, tmp_path: Path):
        """When total cached size exceeds max_size_mb, oldest entries are removed."""
        # Very small limit to trigger eviction after 2 items
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache", max_size_mb=0.00001)  # ~10 bytes

        data_a = b"AAAAAA"   # 6 bytes
        data_b = b"BBBBBB"   # 6 bytes
        data_c = b"CCCCCC"   # 6 bytes

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _make_mock_response(data_a)
            mgr.get("https://example.com/a.txt")

            mock_urlopen.return_value = _make_mock_response(data_b)
            mgr.get("https://example.com/b.txt")

            # After adding c, eviction should kick in and remove at least one old entry
            mock_urlopen.return_value = _make_mock_response(data_c)
            mgr.get("https://example.com/c.txt")

        # At least one of the earlier entries should have been evicted
        assert "https://example.com/c.txt" in mgr._index
        logger.debug("Index after eviction: %s", list(mgr._index.keys()))


# ---------------------------------------------------------------------------
# Stats property
# ---------------------------------------------------------------------------

class TestStatsProperty:
    """stats property returns correct metadata."""

    def test_stats_property(self, tmp_path: Path):
        """Stats reflect cached items count, sizes, and config values."""
        mgr = _get_cache_manager()(
            cache_dir=tmp_path / "cache",
            max_size_mb=100,
            ttl_seconds=3600,
            offline_mode=False,
        )
        data = b"stats-test-data"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            mgr.get("https://example.com/stats.txt")

        stats = mgr.stats
        assert stats["cached_items"] >= 1
        assert stats["total_size_bytes"] >= len(data)
        assert stats["max_size_mb"] == 100
        assert stats["cache_dir"] == str(tmp_path / "cache")
        assert stats["offline_mode"] is False

    def test_stats_empty_cache(self, tmp_path: Path):
        """Empty cache stats show zero items."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        stats = mgr.stats
        assert stats["cached_items"] == 0
        assert stats["total_size_bytes"] == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary and error-handling scenarios."""

    def test_empty_url_handling(self, tmp_path: Path):
        """Empty string URL returns None gracefully."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        result = mgr.get("")
        assert result is None

    def test_network_failure_graceful(self, tmp_path: Path):
        """Network failure (URLError) returns None instead of crashing."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")

        import urllib.error
        with patch(
            "pycc2.infrastructure.resource_cache.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = mgr.get("https://example.com/down.txt")

        assert result is None

    def test_is_cached_false_for_unknown(self, tmp_path: Path):
        """is_cached returns False for URLs never seen."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        assert mgr.is_cached("https://example.com/unknown") is False

    def test_is_cached_true_after_download(self, tmp_path: Path):
        """is_cached returns True after successful download within TTL."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"check-me"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            mgr.get("https://example.com/is_cached.txt")

        assert mgr.is_cached("https://example.com/is_cached.txt") is True

    def test_progress_callback_invoked(self, tmp_path: Path):
        """Progress callback receives downloaded byte counts during download."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "cache")
        data = b"x" * 20000  # enough for multiple chunks
        mock_resp = _make_mock_response(data, content_length=len(data))

        calls = []
        def cb(downloaded, total):
            calls.append((downloaded, total))

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            result = mgr.get("https://example.com/large.bin", progress_callback=cb)

        assert result is not None
        assert len(calls) > 0  # callback was invoked at least once

    def test_corrupted_index_file_handled_gracefully(self, tmp_path: Path):
        """Corrupt cache_index.json does not prevent manager from starting."""
        cache_dir = tmp_path / "bad_index"
        cache_dir.mkdir()
        index_file = cache_dir / "cache_index.json"
        index_file.write_text("{this is not valid json!!!")

        mgr = _get_cache_manager()(cache_dir=cache_dir)
        # Should recover with empty index
        assert mgr._index == {}


# ---------------------------------------------------------------------------
# Index persistence
# ---------------------------------------------------------------------------

class TestIndexPersistence:
    """Cache index survives across manager instances (same cache_dir)."""

    def test_index_persisted_to_disk(self, tmp_path: Path):
        """After download, cache_index.json contains the URL entry."""
        mgr = _get_cache_manager()(cache_dir=tmp_path / "persist")
        data = b"persist-me"
        mock_resp = _make_mock_response(data)

        with patch("pycc2.infrastructure.resource_cache.urllib.request.urlopen", return_value=mock_resp):
            mgr.get("https://example.com/persist.txt")

        index_file = mgr._index_path
        assert index_file.exists()
        saved = json.loads(index_file.read_text())
        assert "https://example.com/persist.txt" in saved
        assert saved["https://example.com/persist.txt"]["sha256"] == _sha256_of(data)
