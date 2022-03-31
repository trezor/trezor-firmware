from . import UI2

if UI2:
    from .tt_v2.altcoin import *  # noqa: F401,F403
else:
    from .tt.altcoin import *  # noqa: F401,F403
