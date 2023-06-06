from trezor import utils

if utils.MODEL in ("T", "T3W1", "DISC1"):
    from .tt_v2.reset import *  # noqa: F401,F403
elif utils.MODEL in ("R",):
    from .tr.reset import *  # noqa: F401,F403
