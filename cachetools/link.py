class Link(object):
    __slots__ = 'prev', 'next', 'data'

    def unlink(self):
        next = self.next
        prev = self.prev
        prev.next = next
        next.prev = prev
        del self.next
        del self.prev
