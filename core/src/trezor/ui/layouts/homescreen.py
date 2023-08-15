from trezor import utils

if utils.INTERNAL_MODEL in ("T2T1", "D001"):
    from .tt_v2.homescreen import *  # noqa: F401,F403
elif utils.INTERNAL_MODEL in ("T2B1",):
    from .tr.homescreen import *  # noqa: F401,F403
