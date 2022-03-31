from . import UI2

if UI2:
    from .tt_v2.reset import *  # noqa: F401,F403
else:
    from .tt.reset import *  # noqa: F401,F403
