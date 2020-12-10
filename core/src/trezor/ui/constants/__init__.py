from trezor import utils

# from .common import *

if utils.MODEL == "1":
    from .t1 import *
elif utils.MODEL == "T":
    from .tt import *
else:
    raise ValueError("Unknown Trezor model")
