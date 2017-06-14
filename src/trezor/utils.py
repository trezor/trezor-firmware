import sys
import gc

from trezorutils import halt, memcpy

type_gen = type((lambda: (yield))())
type_genfunc = type((lambda: (yield)))


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


def _unimport_genfunc(genfunc):
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
    if isinstance(func, type_genfunc):
        return _unimport_genfunc(func)
    else:
        return _unimport_func(func)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def ensure(cond):
    if not cond:
        raise AssertionError()
