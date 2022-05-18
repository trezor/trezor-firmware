from trezor import utils

from . import UI2

if UI2:
    if utils.MODEL in ("T",):
        from .tt_v2.altcoin import *  # noqa: F401,F403
    elif utils.MODEL in ("R",):
        from .tr.altcoin import *  # noqa: F401,F403
else:
    from .tt.altcoin import *  # noqa: F401,F403
