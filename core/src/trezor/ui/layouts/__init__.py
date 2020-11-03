from trezor import utils

from .common import *

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       layout type signatures across models
if utils.MODEL == "1":
    from .t1 import *
elif utils.MODEL == "T":
    from .tt import *
else:
    raise ValueError("Unknown Trezor model")
