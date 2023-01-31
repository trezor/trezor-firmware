from trezor import utils

if utils.MODEL in ("T",):
    from .tt_v2.progress import *  # noqa: F401,F403
elif utils.MODEL in ("R",):
    from .tr.progress import *  # noqa: F401,F403
