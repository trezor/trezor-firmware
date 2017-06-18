import sys
import gc

from trezorutils import halt, memcpy


def _gf():
    yield


type_gen = type(_gf())


def _unimport_func(func):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = func(*args, **kwargs)
        finally:
            for mod in sys.modules:
                if mod not in mods:
                    del sys.modules[mod]
            gc.collect()
        return ret
    return inner


def _unimport_gen(genfunc):
    async def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = await genfunc(*args, **kwargs)
        finally:
            for mod in sys.modules:
                if mod not in mods:
                    del sys.modules[mod]
            gc.collect()
        return ret
    return inner


def unimport(func):
    if isinstance(func, type_gen):
        return _unimport_gen(func)
    else:
        return _unimport_func(func)


def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def ensure(cond):
    if not cond:
        raise AssertionError()
