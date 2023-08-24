from trezor import utils

if utils.UI_LAYOUT == "TT":
    from .tt.fido import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "TR":
    from .tr.fido import *  # noqa: F401,F403
