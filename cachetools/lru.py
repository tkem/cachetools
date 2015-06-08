from .cache import Cache


class Link(object):

    __slots__ = 'key', 'value', 'prev', 'next'

    def unlink(self):
        next = self.next
        prev = self.prev
        prev.next = next
        next.prev = prev


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, maxsize, missing=None, getsizeof=None):
        self.__getsizeoflink = None
        if getsizeof is not None:
            Cache.__init__(self, maxsize, missing, lambda link: getsizeof(link.value))
            self.__getsizeoflink = getsizeof
        else:
            Cache.__init__(self, maxsize, missing)
        self.__root = root = Link()
        root.prev = root.next = root

    def getsizeof(self, value):
        if self.__getsizeoflink:
            return self.__getsizeoflink(value)
        return Cache.getsizeof(self, value)

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
        link = Link()
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
