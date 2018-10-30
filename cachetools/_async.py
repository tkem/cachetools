
def func_wrapper(func, cache, key):
    async def wrapper(*args, **kwargs):
        k = key(*args, **kwargs)
        try:
            return cache[k]
        except KeyError:
            pass  # key not found
        v = await func(*args, **kwargs)
        try:
            cache[k] = v
        except ValueError:
            pass  # value too large
        return v

    return wrapper


def func_wrapper_lock(func, cache, key, lock):
    async def wrapper(*args, **kwargs):
        k = key(*args, **kwargs)
        try:
            with lock:
                return cache[k]
        except KeyError:
            pass  # key not found
        v = await func(*args, **kwargs)
        try:
            with lock:
                cache[k] = v
        except ValueError:
            pass  # value too large
        return v

    return wrapper


def method_wrapper(method, cache, key):
    async def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            v = await method(self, *args, **kwargs)
            return v
        k = key(self, *args, **kwargs)
        try:
            return c[k]
        except KeyError:
            pass  # key not found
        v = await method(self, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    return wrapper


def method_wrapper_lock(method, cache, key, lock):
    async def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            v = await method(self, *args, **kwargs)
            return v
        k = key(self, *args, **kwargs)
        try:
            with lock(self):
                return c[k]
        except KeyError:
            pass  # key not found
        v = await method(self, *args, **kwargs)
        try:
            with lock(self):
                c[k] = v
        except ValueError:
            pass  # value too large
        return v

    return wrapper
