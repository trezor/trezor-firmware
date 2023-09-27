from trezor import utils

if utils.UI_LAYOUT == "TT":
    from .tt.homescreen import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "TR":
    from .tr.homescreen import *  # noqa: F401,F403
