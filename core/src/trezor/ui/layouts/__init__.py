from trezor import utils

from .common import *  # noqa: F401,F403

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       layout type signatures across models
if utils.INTERNAL_MODEL in ("T1B1", "T2B1"):
    from .tr import *  # noqa: F401,F403
elif utils.INTERNAL_MODEL in ("T2T1", "D001"):
    from .tt_v2 import *  # noqa: F401,F403
else:
    raise ValueError("Unknown Trezor model")
