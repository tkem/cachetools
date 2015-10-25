from __future__ import absolute_import

import collections

from abc import ABCMeta, abstractmethod


class Missing:  # TBD: "Missable"? "Missed"?

    __metaclass__ = ABCMeta

    __slots__ = ()

    # TBD: abstract?
    def __missing__(self, key):
        raise KeyError(key)

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Missing:
            if any('__missing__' in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented


class MissingMapping(collections.Mapping, Missing):

    __slots__ = ()

    @abstractmethod
    def __getitem__(self, key):
        return self.__missing__(key)

    @abstractmethod
    def __contains__(self, key):
        return False

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default


# TODO: derive fom MissingMapping?
class MissingMutableMapping(collections.MutableMapping, Missing):

    __slots__ = ()

    @abstractmethod
    def __getitem__(self, key):
        return self.__missing__(key)

    @abstractmethod
    def __contains__(self, key):
        return False

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    __marker = object()

    def pop(self, key, default=__marker):
        if key in self:
            value = self[key]
            del self[key]
            return value
        elif default is self.__marker:
            raise KeyError(key)
        else:
            return default

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        else:
            self[key] = default
            return default
