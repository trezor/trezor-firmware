from trezor import utils

if utils.UI_LAYOUT == "TT":
    from .tt.progress import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "TR":
    from .tr.progress import *  # noqa: F401,F403
