from trezor import utils

if utils.MODEL in ("T",):
    from .tt_v2.fido import *  # noqa: F401,F403
elif utils.MODEL in ("R",):
    from .tr.fido import *  # noqa: F401,F403
