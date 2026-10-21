# ECP/BVA notes: LRUCache (Muhammad)

Project: cachetools 7.2.4. Class under test: `LRUCache` (parent `Cache`).
Unless stated otherwise, every value has size 1 (the default `getsizeof`).
Every row was checked by running the code.

## __setitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 0, set one item (size 1) | Boundary: smallest capacity, value larger than maxsize | Raises ValueError("value too large"); cache stays empty |
| maxsize = 1, set one item (size 1) | Boundary: value size exactly equals maxsize | Stored, no eviction; currsize = 1 |
| maxsize = 2, set three items a, b, c | Boundary: one more item than capacity | a (least recently used) is evicted; cache holds b and c; currsize = 2 |
| maxsize = 2, set a, b, then overwrite a, then set c | Existing key: overwrite refreshes recency | b is evicted; cache holds a and c |
| maxsize = 3, getsizeof=len, set a='x', b='yy', then overwrite a='zz' | Existing key: overwrite with a larger size, key itself is the LRU | a and b both evicted, a stored again; list = ['a'], currsize = 2 |
| maxsize = 3, getsizeof=len, set a='xxx' (size 3) | Boundary: value size exactly equals maxsize | Stored; currsize = 3 |
| maxsize = 3, getsizeof=len, set b='xxxx' (size 4) | Boundary: value size one above maxsize | Raises ValueError("value too large") |
| maxsize = 3, getsizeof=len, a='xxx' stored, then set b='xxxx' (size 4) fails | Failed insert leaves cache unchanged | a still present; list = ['a'], currsize = 3 |
| maxsize = 2, key = None | Key partition: valid hashable special value | Stored like any other key; list = [None] |
| maxsize = 2, key = [1, 2] (list) | Key partition: unhashable key | Raises TypeError (unhashable type: 'list'); cache unchanged |
| maxsize = 2, getsizeof=lambda v: v, set a=-1 | Value size just below zero | Raises ValueError("value size must be non-negative"); nothing stored |
| maxsize = 2, getsizeof=lambda v: v, set a=0 | Boundary: smallest valid value size | Stored; currsize = 0; list = ['a'] |

## __getitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a, b, read a, then set c | Existing key: read refreshes recency | b is evicted; list = ['a', 'c'] |
| maxsize = 2, set a, read missing key 'zzz' | Missing key | Raises KeyError('zzz'); cache unchanged, list = ['a'], currsize = 1 |
| maxsize = 2, set a, b, call get('a'), then set c | Inherited get() on an existing key | Also refreshes recency; list = ['a', 'c'] |
| maxsize = 2, set a, b, check 'a' in cache, then set c | Membership check (__contains__) | Does not refresh recency; b and c remain, a is evicted |

## __delitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a, b, delete a | Existing key | Removed; list = ['b'], currsize = 1 |
| maxsize = 2, set b, delete missing key 'zzz' | Missing key | Raises KeyError('zzz'); list = ['b'], currsize = 1 |
| maxsize = 2, set a, b, delete a, set a again, then set c | Delete, then reinsert the same key | Reinserted a counts as most recent; b is evicted, list = ['a', 'c'] |

## popitem

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 3, set a=1, b=2, c=3, popitem | Normal case: full cache | Returns ('a', 1); list = ['b', 'c'], currsize = 2 |
| maxsize = 3, set a, b, c, read a, popitem | Read changes which item is LRU | Returns ('b', 2) |
| maxsize = 3, set a, b, overwrite a, popitem | Overwrite changes which item is LRU | Returns ('b', 2) |
| empty cache, popitem | Boundary: empty | Raises KeyError('LRUCache is empty') |
| maxsize = 1, set a, popitem twice | Boundary: last item removed, then empty | First returns ('a', 1); second raises KeyError('LRUCache is empty') |

## clear

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 2, set a, b, clear | Full cache | list = [], currsize = 0, len = 0 |
| cleared cache, popitem | Order tracking is also reset | Raises KeyError('LRUCache is empty') |
| cleared cache, set x, y, z with maxsize 2 | Cache is reusable after clear | list = ['y', 'z'] |
| empty cache, clear | Boundary: already empty | No error; list = [], currsize = 0 |

## __init__ / maxsize

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| LRUCache(2) | Valid maxsize | maxsize property returns 2 |
| LRUCache(-1), then set one item | Invalid: negative maxsize | Raises ValueError("maxsize must be non-negative") |

## TTLCache (expiry half: ttl, timer, __contains__, __iter__, expire)

Tests use a fake clock (a callable whose value I set by hand), so no `sleep()` is needed.
Rule found in the code: an item is valid while `now < time_set + ttl`. At exactly `time_set + ttl` it is already expired.

### ttl

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| TTLCache(3, ttl=10) | Typical integer ttl | ttl property returns 10 |
| TTLCache(3, ttl=0.5) | Non-integer ttl | ttl property returns 0.5 |
| TTLCache(3, ttl=0), set a | Boundary: smallest ttl | a is already expired: 'a' not in cache, len = 0 |
| TTLCache(3, ttl=-5), set a | Invalid: negative ttl | a is already expired: 'a' not in cache, len = 0 (no error is raised) |

### timer

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| Custom clock at 0 | Timer property with a custom clock | cache.timer() returns 0 |
| Custom clock advanced to 5 | Timer follows the clock | cache.timer() returns 5 |
| No timer given | Default timer | cache.timer is callable and returns a float |
| Default timer, set x | Default timer works for fresh items | 'x' in cache is True |
| maxsize = 2, ttl = 10, set a at t=0, b at t=5, then set c at t=11 | Timer drives expiry on insert | Expired a is removed first; list = ['b', 'c'] |

### __contains__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| ttl = 10, a set at t=0, check at t=0 | Boundary: just set | True |
| check at t=9 | Partition: well before expiry | True |
| check at t=9.99 | Boundary: just before expiry | True |
| check at t=10 | Boundary: exactly at expiry | False |
| check at t=10.01 | Boundary: just after expiry | False |
| check at t=11 | Partition: well after expiry | False |
| key never set | Missing key | False |
| a set at t=0, overwritten at t=8, check at t=12 and t=18 | Overwrite resets the expiry | True at 12, False at 18 |

### __iter__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| ttl = 10, a at t=0, b at t=3, c at t=6, iterate at t=9 | Nothing expired | ['a', 'b', 'c'] |
| same cache, iterate at t=10 | Boundary: first item expires exactly now | ['b', 'c'] |
| same cache, iterate at t=13 | Two items expired | ['c'] |
| same cache, iterate at t=16 | All expired | [] |
| empty cache | Boundary: empty | [] |
| a and b set at t=0, iterate at t=10 | All items expired at once | [], len = 0, currsize = 0 |

### expire

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| ttl = 10, a at t=0, b at t=5, expire() at t=9 | Nothing expired | Returns [] |
| same cache, expire() at t=10 | Boundary: a expires exactly now | Returns [('a', 1)]; list = ['b'] |
| same cache, expire() at t=20 | Remaining item expired | Returns [('b', 2)]; list = [] |
| empty cache, expire() | Boundary: empty | Returns [] |
| a, b set at t=0, clock still 0, expire(10) | Explicit time argument overrides the clock | Returns [('a', 1), ('b', 2)]; list = [], currsize = 0 |
| a set at t=0, expire(9.99) | Explicit time just before expiry | Returns []; list = ['a'] |
| a at t=0, b at t=1, c at t=2, expire() at t=20 | Several expired at once | Returned in the order they were set: a, b, c |