"""Tests for LRUTTLCache."""

import unittest

from lru_ttl_cache import LRUTTLCache


class FakeClock:
    """A deterministic clock that only advances when manually stepped."""

    def __init__(self, start: float = 0.0):
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


class TestLRUTTLCache(unittest.TestCase):
    def test_put_and_get(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=10, clock=clock)
        cache.put("a", 1)
        self.assertEqual(cache.get("a"), 1)

    def test_missing_key_returns_default(self):
        cache = LRUTTLCache(maxsize=2, ttl=10, clock=FakeClock())
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", "fallback"), "fallback")

    def test_ttl_expiry(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(5.0)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(len(cache), 0)

    def test_ttl_boundary_is_inclusive(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(4.999)
        self.assertEqual(cache.get("a"), 1)
        clock.advance(0.001)
        self.assertIsNone(cache.get("a"))

    def test_lru_eviction(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=100, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # make a most recently used
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)

    def test_update_existing_key(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=10, clock=clock)
        cache.put("a", 1)
        cache.put("a", 2)
        self.assertEqual(cache.get("a"), 2)

    def test_update_resets_ttl(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=5, clock=clock)
        cache.put("a", 1)
        clock.advance(4)
        cache.put("a", 2)  # reset TTL
        clock.advance(4)
        self.assertEqual(cache.get("a"), 2)

    def test_contains(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=5, clock=clock)
        cache.put("a", 1)
        self.assertTrue(cache.contains("a"))
        clock.advance(5)
        self.assertFalse(cache.contains("a"))

    def test_peek_does_not_change_lru_order(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=2, ttl=100, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.peek("a")
        cache.put("c", 3)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)

    def test_purge_removes_only_expired(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=3, ttl=10, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        clock.advance(11)
        cache.put("d", 4)  # this will purge expired and evict
        # after put d: a,b,c all expired, d live, so len should be 1
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get("d"), 4)

    def test_clear(self):
        clock = FakeClock()
        cache = LRUTTLCache(maxsize=3, ttl=10, clock=clock)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        self.assertEqual(len(cache), 0)
        self.assertIsNone(cache.get("a"))

    def test_invalid_maxsize(self):
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=0, ttl=10)
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=-1, ttl=10)

    def test_invalid_ttl(self):
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=2, ttl=0)
        with self.assertRaises(ValueError):
            LRUTTLCache(maxsize=2, ttl=-1)


if __name__ == "__main__":
    unittest.main()
