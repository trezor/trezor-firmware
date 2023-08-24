from trezor import utils

if utils.LAYOUT == "TTV2":
    from .tt_v2.recovery import *  # noqa: F401,F403
elif utils.LAYOUT == "TR":
    from .tr.recovery import *  # noqa: F401,F403
