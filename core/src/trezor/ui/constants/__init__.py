from trezor import utils

if utils.MODEL == "1":
    from .t1 import *  # noqa: F401,F403
elif utils.MODEL == "T":
    from .tt import *  # noqa: F401,F403
else:
    raise ValueError("Unknown Trezor model")
