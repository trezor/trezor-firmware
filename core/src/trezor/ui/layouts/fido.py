from trezor import utils

if utils.LAYOUT == "TTV2":
    from .tt_v2.fido import *  # noqa: F401,F403
elif utils.LAYOUT == "TR":
    from .tr.fido import *  # noqa: F401,F403
