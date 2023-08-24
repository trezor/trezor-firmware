from trezor import utils

from .common import *  # noqa: F401,F403

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       layout type signatures across models
if utils.LAYOUT == "TR":
    from .tr import *  # noqa: F401,F403
elif utils.LAYOUT == "TTV2":
    from .tt_v2 import *  # noqa: F401,F403
else:
    raise ValueError("Unknown layout")
