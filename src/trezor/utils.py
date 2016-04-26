import sys
import gc

def unimport(func):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        ret = func(*args, **kwargs)
        for to_remove in set(sys.modules) - mods:
            print(to_remove)
            del sys.modules[to_remove]
        return ret
    return inner
