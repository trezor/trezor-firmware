from trezor import utils

if utils.UI_LAYOUT == "BOLT":
    from .bolt.reset import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "SAMSON":
    from .samson.reset import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "QUICKSILVER":
    from .quicksilver.reset import *  # noqa: F401,F403
