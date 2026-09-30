# LRU TTL Cache

A thread-safe least-recently-used cache where each entry expires after a fixed time-to-live (TTL).

```python
from lru_ttl_cache import LRUTTLCache

cache = LRUTTLCache(maxsize=100, ttl=60.0)
cache.put("user:42", {"name": "Alice"})
print(cache.get("user:42"))  # {'name': 'Alice'}
```

## Why this exists

In-memory caches often need both a size limit and a freshness guarantee. A pure LRU cache serves stale data forever; a pure TTL cache can grow without bound. This cache combines the two by evicting the least recently used entry when at capacity and lazily expiring entries whose TTL has passed. The design favours simplicity and predictability: expired entries are only removed when the cache is accessed, avoiding background threads and timer overhead.

## Behaviour notes

- `put` resets the TTL for an existing key.
- `get` marks an entry as most recently used; `peek` does not.
- Expired entries are removed lazily on access. `purge` forces immediate removal.
- The cache is thread-safe; all public methods acquire an internal lock.
- The clock is injectable via the `clock` constructor argument, which must be a zero-argument callable returning seconds (e.g. `time.monotonic`).

## Edge cases

- If `maxsize` is less than 1 or `ttl` is not positive, a `ValueError` is raised.
- Expiry is inclusive: an entry expires when the clock reaches `insertion_time + ttl`.
- `get` returns `None` for missing or expired entries; use the `default` parameter to distinguish.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

