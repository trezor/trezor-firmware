from trezor import utils

if utils.UI_LAYOUT == "BOLT":
    from .bolt.recovery import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "CAESAR":
    from .caesar.recovery import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "DELIZIA":
    from .delizia.recovery import *  # noqa: F401,F403
