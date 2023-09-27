from trezor import utils

from .common import *  # noqa: F401,F403

# NOTE: using any import magic probably causes mypy not to check equivalence of
#       layout type signatures across models
if utils.UI_LAYOUT == "TR":
    from .tr import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "TT":
    from .tt import *  # noqa: F401,F403
else:
    raise ValueError("Unknown layout")
