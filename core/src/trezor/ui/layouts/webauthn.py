from . import UI2

if UI2:
    from .tt_v2.webauthn import *  # noqa: F401,F403
else:
    from .tt.webauthn import *  # noqa: F401,F403
