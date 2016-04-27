import sys
import gc
from TrezorUtils import Utils

_utils = Utils()

def memaccess(address, length):
    return _utils.memaccess(address, length)

def unimport(func):
    def inner(*args, **kwargs):
        mods = set(sys.modules)
        ret = func(*args, **kwargs)
        for to_remove in set(sys.modules) - mods:
            print(to_remove)
            del sys.modules[to_remove]
        return ret
    return inner
