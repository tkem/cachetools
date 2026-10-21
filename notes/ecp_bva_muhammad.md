# ECP/BVA notes: LRUCache (Muhammad)

## __setitem__

| Input / condition | Partition or boundary | Expected result |
|---|---|---|
| maxsize = 0, set one item (size 1) | Boundary: smallest capacity, value larger than maxsize | Raises ValueError("value too large"); cache stays empty |
| maxsize = 1, set one item (size 1) | Boundary: value size exactly equals maxsize | Stored, no eviction; currsize = 1 |
| maxsize = 2, set three items a, b, c | Boundary: one more item than capacity | a (least recently used) is evicted; cache holds b and c; currsize = 2 |