from trezor import utils

if utils.UI_LAYOUT == "TT":
    from .tt.sdcard_eject import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "TR":
    raise ValueError("Unsupported layout")
