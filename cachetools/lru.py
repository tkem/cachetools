from .cache import Cache


class _Link(object):

    __slots__ = 'key', 'prev', 'next'

    def __getstate__(self):
        if hasattr(self, 'key'):
            return (self.key,)
        else:
            return None

    def __setstate__(self, state):
        self.key, = state

    def insert(self, next):
        self.next = next
        self.prev = prev = next.prev
        prev.next = next.prev = self

    def unlink(self):
        next = self.next
        prev = self.prev
        prev.next = next
        next.prev = prev


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, maxsize, missing=None, getsizeof=None):
        Cache.__init__(self, maxsize, missing, getsizeof)
        self.__root = root = _Link()
        root.prev = root.next = root
        self.__links = {}

    def __repr__(self, cache_getitem=Cache.__getitem__):
        # prevent item reordering
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key)) for key in self],
            self.maxsize,
            self.currsize,
        )

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        link = self.__links[key]
        link.unlink()
        link.insert(self.__root)
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        try:
            link = self.__links[key]
        except KeyError:
            link = self.__links[key] = _Link()
        else:
            link.unlink()
        link.key = key
        link.insert(self.__root)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        links = self.__links
        links[key].unlink()
        del links[key]

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

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        root = self.__root
        link = root.next
        if link is root:
            raise KeyError('%s is empty' % self.__class__.__name__)
        key = link.key
        return (key, self.pop(key))
