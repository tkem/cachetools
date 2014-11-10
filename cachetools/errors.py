class ExpiredError(KeyError):
    """Raised when a cached item's time-to-live has expired.

    This is a subclass of :exc:`KeyError`.

    """
    pass
