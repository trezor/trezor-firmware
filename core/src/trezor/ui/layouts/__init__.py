from trezor import utils

from .common import *  # noqa: F401,F403

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       layout type signatures across models
if utils.MODEL == "1":
    from .t1 import *  # noqa: F401,F403
elif utils.MODEL == "T":
    from .tt import *  # noqa: F401,F403
else:
    raise ValueError("Unknown Trezor model")
