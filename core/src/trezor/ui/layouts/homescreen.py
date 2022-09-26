from . import UI2

if UI2:
    from .tt_v2.homescreen import *  # noqa: F401,F403
else:
    from .tt.homescreen import *  # noqa: F401,F403
