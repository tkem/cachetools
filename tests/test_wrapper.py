import unittest

import cachetools

from . import DecoratorTestMixin


class CacheWrapperTest(unittest.TestCase, DecoratorTestMixin):

    def cache(self, minsize):
        return cachetools.Cache(maxsize=minsize)


class DictWrapperTest(unittest.TestCase, DecoratorTestMixin):

    def cache(self, minsize):
        return dict()
