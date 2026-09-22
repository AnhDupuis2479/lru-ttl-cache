"""Core implementation of LRUTTLCache."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUTTLCache(Generic[K, V]):
    """A thread-safe LRU cache with per-entry TTL expiry.

    Entries are evicted either because they exceed ``maxsize`` (least recently
    used first) or because their TTL has elapsed. Expired entries are only
    physically removed when they are accessed or during a ``purge`` call.
    This lazy expiry avoids background threads while keeping memory bounded by
    ``maxsize`` plus the number of expired-but-unaccessed entries.

    The clock is injectable via ``clock`` for deterministic tests.
    """

    def __init__(
        self,
        maxsize: int,
        ttl: float,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock if clock is not None else time.monotonic
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        """Return the number of live entries.

        This triggers lazy expiry so the count reflects only non-expired items.
        """
        with self._lock:
            self._purge_expired_locked()
            return len(self._data)

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Return the value for ``key`` or ``default`` if missing or expired.

        On a successful hit the entry is marked as most recently used.
        """
        with self._lock:
            now = self._clock()
            item = self._data.get(key)
            if item is not None:
                expires_at, value = item
                if expires_at > now:
                    self._data.move_to_end(key)
                    return value
                self._data.pop(key, None)
            return default

    def put(self, key: K, value: V) -> None:
        """Insert or update ``key`` with ``value`` and reset its TTL.

        If the cache is at capacity, the least recently used live entry is
        evicted. Expired entries are also removed first to avoid evicting a
        live entry when expired ones are still present.
        """
        with self._lock:
            now = self._clock()
            self._purge_expired_locked()
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (now + self._ttl, value)
            if len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def contains(self, key: K) -> bool:
        """Return True if ``key`` exists and has not expired."""
        with self._lock:
            now = self._clock()
            item = self._data.get(key)
            if item is None:
                return False
            expires_at, _ = item
            if expires_at > now:
                self._data.move_to_end(key)
                return True
            self._data.pop(key, None)
            return False

    def peek(self, key: K) -> Optional[V]:
        """Return the value for ``key`` without changing LRU order.

        Expired entries are treated as missing.
        """
        with self._lock:
            now = self._clock()
            item = self._data.get(key)
            if item is not None:
                expires_at, value = item
                if expires_at > now:
                    return value
                self._data.pop(key, None)
            return None

    def purge(self) -> int:
        """Remove all expired entries and return the number removed."""
        with self._lock:
            now = self._clock()
            expired_keys = [
                key for key, (expires_at, _) in self._data.items() if expires_at <= now
            ]
            for key in expired_keys:
                del self._data[key]
            return len(expired_keys)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._data.clear()

    def _purge_expired_locked(self) -> None:
        """Internal helper: remove expired entries while holding the lock."""
        now = self._clock()
        expired_keys = [
            key for key, (expires_at, _) in self._data.items() if expires_at <= now
        ]
        for key in expired_keys:
            del self._data[key]
