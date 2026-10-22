# ECP/BVA notes: LFUCache and TTLCache basics (Mian)

Project: cachetools 7.2.4. Classes under test: `LFUCache` (parent `Cache`) and the
basic methods of `TTLCache` (parent `_TimedCache`). The expiry methods of `TTLCache`
(`ttl`, `timer`, `__contains__`, `__iter__`, `expire`) are covered in Muhammad's notes.
Unless stated otherwise, every value has size 1 (the default `getsizeof`).
Every row was checked by running the code.

**Important finding:** when two or more keys have the same use count, `LFUCache.popitem`
removes an arbitrary one (it takes the first element of a Python `set`). Which key goes
depends on string hashing, so it can differ between runs. These notes and tests avoid ties:
every eviction case has exactly one key with the lowest count.

## LFUCache: __setitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 0, set one item | Boundary: smallest capacity | Raises ValueError("value too large"); cache stays empty |
| maxsize = 2, set a, b | Boundary: exactly at capacity | Both stored, no eviction; currsize = 2 |
| maxsize = 1, set a, then b | Boundary: capacity of one | a evicted; list = ['b'] |
| maxsize = 2, set a, b, read a, then set c | Over capacity: lowest use count is evicted | b (count 1) is evicted; list = ['a', 'c'] |
| maxsize = 2, set a, b, overwrite a, then set c | Existing key: overwrite counts as a use | b is evicted; list = ['a', 'c']; a holds the new value |
| maxsize = 2, set a, read a twice, set b, then set c | High-count key survives | b is evicted; list = ['a', 'c'] |
| maxsize = 3, getsizeof=len, set 'xxx' (size 3) | Boundary: value size exactly equals maxsize | Stored; currsize = 3 |
| maxsize = 3, getsizeof=len, set 'xxxx' (size 4) | Boundary: value size one above maxsize | Raises ValueError("value too large"); cache unchanged |
| maxsize = 2, key = None | Key partition: valid hashable special value | Stored; list = [None] |
| maxsize = 2, key = [1, 2] (list) | Key partition: unhashable key | Raises TypeError; cache unchanged |

## LFUCache: __getitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a, b, read a, set c | Read raises the use count | b is evicted; list = ['a', 'c'] |
| maxsize = 2, set a, read missing key 'zzz' | Missing key | Raises KeyError; cache unchanged |
| maxsize = 2, set a, b, get('a'), set c | Inherited get() counts as a use | b is evicted; list = ['a', 'c'] |
| maxsize = 2, get('zzz', 'fallback') | get() on a missing key | Returns 'fallback' |
| maxsize = 2, a read 2 times, b read 1 time, then 'b' in cache checked 3 times, then set c | Membership check does not count as a use | b is evicted (count stays 2 vs a's 3); list = ['a', 'c'] |

## LFUCache: __delitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a, b, delete a | Existing key | Removed; list = ['b'], currsize = 1 |
| maxsize = 2, set a, delete missing key 'zzz' | Missing key | Raises KeyError; list = ['a'], currsize = 1 |
| maxsize = 2, set a, b, delete a, set c | Delete frees capacity | Nothing is evicted; both b and c present |
| maxsize = 2, set a, read a 3 times, delete a, set a again, set b, read b, set c | Deleted key starts again at count 1 | a is evicted (count 1 vs b's 2); list = ['b', 'c'] |

## LFUCache: popitem

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 3, set a=1, b=2, c=3, read a twice, read b once, popitem | Normal case: one key with the lowest count | Returns ('c', 3); list = ['a', 'b'], currsize = 2 |
| empty cache, popitem | Boundary: empty | Raises KeyError('LFUCache is empty') |
| maxsize = 1, set a, popitem twice | Boundary: last item removed, then empty | First returns ('a', 1); second raises KeyError('LFUCache is empty') |
| maxsize = 2, set a, b, read b, popitem | Read protects a key from popitem | Returns ('a', 1) |

## LFUCache: clear

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a, b, clear | Full cache | list = [], currsize = 0, len = 0 |
| cleared cache, popitem | Count tracking is reset too | Raises KeyError('LFUCache is empty') |
| after clear, set x, read x, set y, set z with maxsize 2 | Cache is reusable with fresh counts | y is evicted (count 1 vs x's 2); list = ['x', 'z'] |
| empty cache, clear | Boundary: already empty | No error; list = [], currsize = 0 |

## LFUCache: __init__ / maxsize

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| LFUCache(2) | Valid maxsize | maxsize property returns 2 |
| LFUCache(-1), then set one item | Invalid: negative maxsize | Raises ValueError("maxsize must be non-negative") |
| LFUCache(3) | New cache | len = 0, currsize = 0 |

## TTLCache: __init__ / maxsize / ttl argument

Tests use a fake clock (a callable whose value is set by hand), so no `sleep()` is needed.
Rule found in the code: an item is valid while `now < time_set + ttl`.

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| TTLCache(3, ttl=10, timer=clock) | New cache | len = 0, currsize = 0, maxsize = 3 |
| TTLCache(-1, ttl=10, timer=clock), then set one item | Invalid: negative maxsize | Raises ValueError("maxsize must be non-negative") |

## TTLCache: __setitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a=1, b=2 | Within capacity | Both readable; len = 2, currsize = 2 |
| maxsize = 2, set a, b, c | Over capacity | a (least recently used) evicted; list = ['b', 'c'] |
| maxsize = 0, set one item | Boundary: smallest capacity | Raises ValueError("value too large") |
| ttl = 10, a set at t=0, overwritten at t=8, read at t=12 | Overwrite resets the expiry | Returns the new value |
| key = [1, 2] (list) | Key partition: unhashable key | Raises TypeError |

## TTLCache: __getitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| ttl = 10, a set at t=0, read at t=9.99 | Boundary: just before expiry | Returns the value |
| same cache, read at t=10 | Boundary: exactly at expiry | Raises KeyError |
| missing key 'zzz' | Missing key | Raises KeyError |
| maxsize = 2, set a, b, read a, set c | Read refreshes recency | b is evicted; list = ['a', 'c'] |
| ttl = 10, a set at t=0, read at t=50 | Long after expiry | Raises KeyError |

## TTLCache: __delitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 3, set a, b, delete a | Existing key | list = ['b'], len = 1 |
| delete missing key 'zzz' | Missing key | Raises KeyError |
| ttl = 10, a set at t=0, delete a at t=10 | Key already expired | Raises KeyError, and a is gone afterwards |
| maxsize = 2, set a, b, delete a, set c | Delete frees capacity | Nothing is evicted; both b and c present |

## TTLCache: popitem

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 3, a set at t=0, b at t=5, popitem | Normal case | Returns ('a', 1); list = ['b'] |
| ttl = 10, a at t=0, b at t=5, popitem at t=11 | Expired item is skipped | Returns ('b', 2) |
| ttl = 10, a set at t=0, popitem at t=11 | Boundary: everything expired | Raises KeyError('TTLCache is empty') |
| empty cache, popitem | Boundary: empty | Raises KeyError('TTLCache is empty') |
| maxsize = 2, set a, b, read a, popitem | Read changes which item is popped | Returns ('b', 2) |

## TTLCache: clear

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 3, set a, b, clear | Full cache | list = [], currsize = 0, len = 0 |
| cleared cache, popitem | Order tracking is reset too | Raises KeyError('TTLCache is empty') |
| cleared cache, set x, y, z with maxsize 2 | Reusable after clear | list = ['y', 'z'] |
| empty cache, clear | Boundary: already empty | No error; list = [], currsize = 0 |

## TTLCache: __len__ / currsize

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| empty cache | Boundary: empty | len = 0, currsize = 0 |
| set a, b (size 1 each) | Normal | len = 2, currsize = 2 |
| ttl = 10, a and b set at t=0, check at t=10 | Boundary: all expired | len = 0, currsize = 0 |
| ttl = 10, a at t=0, b at t=5, check at t=10 | Partial expiry | len = 1, currsize = 1 |
| getsizeof=len, set 'xx' and 'yyy' | Currsize sums value sizes | len = 2, currsize = 5 |
