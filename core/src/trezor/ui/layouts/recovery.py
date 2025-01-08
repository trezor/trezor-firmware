from trezor import utils

if utils.UI_LAYOUT == "BOLT":
    from .bolt.recovery import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "SAMSON":
    from .samson.recovery import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "QUICKSILVER":
    from .quicksilver.recovery import *  # noqa: F401,F403
