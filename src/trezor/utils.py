import sys
import gc

from trezor import log

type_gen = type((lambda: (yield))())
type_genfunc = type((lambda: (yield)))


def _unimport_func(func):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = func(*args, **kwargs)
        finally:
            for to_remove in set(sys.modules) - mods:
                print('removing module', to_remove)
                # log.info(__name__, 'removing module %s', to_remove)
                del sys.modules[to_remove]
            gc.collect()
        return ret
    return inner


def _unimport_genfunc(genfunc):
    async def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = await genfunc(*args, **kwargs)
        finally:
            for to_remove in set(sys.modules) - mods:
                print('removing module', to_remove)
                # log.info(__name__, 'removing module %s', to_remove)
                del sys.modules[to_remove]
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
