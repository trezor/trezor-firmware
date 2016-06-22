if not __debug__:
    raise ImportError('This module can be loaded only in DEBUG mode')

from TrezorDebug import Debug

_utils = Debug()

def memaccess(address, length):
    return _utils.memaccess(address, length)
