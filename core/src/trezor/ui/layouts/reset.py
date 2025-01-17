from trezor import utils

if utils.UI_LAYOUT == "BOLT":
    from .bolt.reset import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "CAESAR":
    from .caesar.reset import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "DELIZIA":
    from .delizia.reset import *  # noqa: F401,F403
