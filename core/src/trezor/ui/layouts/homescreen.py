from trezor import utils

if utils.LAYOUT == "TTV2":
    from .tt_v2.homescreen import *  # noqa: F401,F403
elif utils.LAYOUT == "TR":
    from .tr.homescreen import *  # noqa: F401,F403
