"""
Livecrawling cache layer - Control content freshness.
Inspired by Exa's maxAgeHours parameter.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Any
from crawlers.base import CrawlResult
import json
import hashlib
import os


@dataclass
class CacheEntry:
    """A cached crawl result"""
    key: str
    result: CrawlResult
    cached_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class LivecrawlCache:
    """
    Cache layer for crawler results with freshness control.

    maxAgeHours behavior:
    - 24: Use cache if <24 hours old, otherwise livecrawl
    - 1: Use cache if <1 hour old, otherwise livecrawl
    - 0: Always livecrawl (ignore cache)
    - -1: Never livecrawl (cache only)
    - None: Default behavior (livecrawl if no cache)
    """

    def __init__(self, cache_dir: str = None, max_size: int = 1000):
        self.cache: dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.cache_dir = cache_dir
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "livecrawls": 0,
        }

    def get(
        self,
        url: str,
        max_age_hours: Optional[int] = None,
    ) -> Optional[CrawlResult]:
        """
        Get cached result if valid.

        Args:
            url: URL to lookup
            max_age_hours: Maximum acceptable cache age in hours
                - 24: Use cache if <24 hours old
                - 1: Use cache if <1 hour old
                - 0: Always livecrawl (return None)
                - -1: Never livecrawl (always return cache)
                - None: Default (return cache if exists)

        Returns:
            CrawlResult if cache hit, None if livecrawl needed
        """
        key = self._make_key(url)
        entry = self.cache.get(key)

        # No cache entry
        if not entry:
            self.stats["misses"] += 1
            return None

        entry.access_count += 1
        entry.last_accessed = datetime.now()

        # Always livecrawl
        if max_age_hours == 0:
            self.stats["livecrawls"] += 1
            return None

        # Never livecrawl (cache only)
        if max_age_hours == -1:
            self.stats["hits"] += 1
            return entry.result

        # Check age
        if max_age_hours is not None:
            age = datetime.now() - entry.cached_at
            if age > timedelta(hours=max_age_hours):
                self.stats["livecrawls"] += 1
                return None

        # Cache hit
        self.stats["hits"] += 1
        return entry.result

    def set(self, url: str, result: CrawlResult):
        """Store a result in cache"""
        key = self._make_key(url)

        # Evict if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()

        self.cache[key] = CacheEntry(
            key=key,
            result=result,
            cached_at=datetime.now(),
        )

    def _make_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.cache:
            return

        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        del self.cache[oldest_key]
        self.stats["evictions"] += 1

    def clear(self):
        """Clear all cache"""
        self.cache.clear()

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0

        return {
            **self.stats,
            "size": len(self.cache),
            "hit_rate": f"{hit_rate:.1%}",
        }


class LivecrawlManager:
    """Manage livecrawling behavior across all crawlers"""

    def __init__(self, cache_dir: str = None):
        self.cache = LivecrawlCache(cache_dir)
        self.default_timeout = 15000  # 15 seconds in ms

    def should_livecrawl(
        self,
        url: str,
        max_age_hours: Optional[int] = None,
    ) -> bool:
        """Determine if we need to livecrawl"""
        cached = self.cache.get(url, max_age_hours)
        return cached is None

    def get_cached(self, url: str, max_age_hours: Optional[int] = None) -> Optional[CrawlResult]:
        """Get from cache"""
        return self.cache.get(url, max_age_hours)

    def store(self, url: str, result: CrawlResult):
        """Store in cache"""
        self.cache.set(url, result)

    def get_stats(self) -> dict:
        """Get cache stats"""
        return self.cache.get_stats()


# Global instance
livecrawl_manager = LivecrawlManager()
