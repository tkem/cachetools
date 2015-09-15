from .base import Cache


class _Link(object):

    __slots__ = 'key', 'value', 'prev', 'next'

    def __getstate__(self):
        if hasattr(self, 'key'):
            return (self.key, self.value)
        else:
            return None

    def __setstate__(self, state):
        self.key, self.value = state

    def unlink(self):
        next = self.next
        prev = self.prev
        prev.next = next
        next.prev = prev


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, maxsize, missing=None, getsizeof=None, callback=None):
        Cache.__init__(self, maxsize, missing, getsizeof, callback)
        root = self.__root = _Link()
        root.prev = root.next = root

    def __repr__(self, cache_getitem=Cache.__getitem__):
        # prevent item reordering
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key).value) for key in self],
            self.maxsize,
            self.currsize,
        )

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        link = cache_getitem(self, key)
        next = link.next
        prev = link.prev
        prev.next = next
        next.prev = prev
        link.next = root = self.__root
        link.prev = tail = root.prev
        tail.next = root.prev = link
        return link.value

    def __setitem__(self, key, value,
                    cache_contains=Cache.__contains__,
                    cache_getitem=Cache.__getitem__,
                    cache_setitem=Cache.__setitem__):
        if cache_contains(self, key):
            oldlink = cache_getitem(self, key)
        else:
            oldlink = None
        link = _Link()
        link.key = key
        link.value = value
        cache_setitem(self, key, link)
        if oldlink:
            oldlink.unlink()
        link.next = root = self.__root
        link.prev = tail = root.prev
        tail.next = root.prev = link

    def __delitem__(self, key,
                    cache_contains=Cache.__contains__,
                    cache_getitem=Cache.__getitem__,
                    cache_delitem=Cache.__delitem__):
        if not cache_contains(self, key):
            raise KeyError(key)
        link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.unlink()

    def __getstate__(self):
        state = self.__dict__.copy()
        root = self.__root
        links = state['__links'] = [root]
        link = root.next
        while link is not root:
            links.append(link)
            link = link.next
        return state

    def __setstate__(self, state):
        links = state.pop('__links')
        count = len(links)
        for index, link in enumerate(links):
            link.prev = links[index - 1]
            link.next = links[(index + 1) % count]
        self.__dict__.update(state)

    def getsizeof(self, value):
        """Return the size of a cache element's value."""
        if isinstance(value, _Link):
            return Cache.getsizeof(self, value.value)
        else:
            return Cache.getsizeof(self, value)

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        root = self.__root
        link = root.next
        if link is root:
            raise KeyError('cache is empty')
        key = link.key
        Cache.__delitem__(self, key)
        link.unlink()
        return (key, link.value)
