import sys
from TrezorUtils import Utils

_utils = Utils()

type_gen = type((lambda: (yield))())

def memaccess(address, length):
    return _utils.memaccess(address, length)

def select(timeout_us):
    return _utils.select(timeout_us)

def unimport_func(func):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = func(*args, **kwargs)
        finally:
            for to_remove in set(sys.modules) - mods:
                del sys.modules[to_remove]
        return ret
    return inner

def unimport_gen(gen):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        try:
            ret = yield from gen(*args, **kwargs)
        finally:
            for to_remove in set(sys.modules) - mods:
                del sys.modules[to_remove]
        return ret
    return inner
