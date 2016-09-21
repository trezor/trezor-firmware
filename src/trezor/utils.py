import sys

type_gen = type((lambda: (yield))())
type_genfunc = type((lambda: (yield)))


def _unimport_func(func):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = func(*args, **kwargs)
        finally:
            for to_remove in set(sys.modules) - mods:
                del sys.modules[to_remove]
        return ret
    return inner


def _unimport_genfunc(genfunc):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = yield from genfunc(*args, **kwargs)
        finally:
            for to_remove in set(sys.modules) - mods:
                del sys.modules[to_remove]
        return ret
    return inner


def unimport(func):
    if isinstance(func, type_genfunc):
        return _unimport_genfunc(func)
    else:
        return _unimport_func(func)


def coroutine(func):
    def inner(*args, **kwargs):
        gen = func(*args, **kwargs)
        gen.send(None)
        return gen
    return inner


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]
