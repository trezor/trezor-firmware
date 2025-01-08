from trezor import utils

if utils.UI_LAYOUT == "BOLT":
    from .bolt.fido import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "SAMSON":
    from .samson.fido import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "QUICKSILVER":
    from .quicksilver.fido import *  # noqa: F401,F403
