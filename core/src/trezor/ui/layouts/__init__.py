from trezor import utils

from .common import *  # noqa: F401,F403

try:
    UI2 = True
    import trezorui2  # noqa: F401
except ImportError:
    UI2 = False

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       layout type signatures across models
if utils.MODEL == "1":
    from .t1 import *  # noqa: F401,F403
elif utils.MODEL == "T":
    if not UI2:
        from .tt import *  # noqa: F401,F403
    else:
        from .tt_v2 import *  # noqa: F401,F403
else:
    raise ValueError("Unknown Trezor model")
