# flake8: noqa

try:
    from threading import RLock
except ImportError:
    from dummy_threading import RLock
