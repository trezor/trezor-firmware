from trezor import utils

if utils.LAYOUT == "TTV2":
    from .tt_v2.progress import *  # noqa: F401,F403
elif utils.LAYOUT == "TR":
    from .tr.progress import *  # noqa: F401,F403
