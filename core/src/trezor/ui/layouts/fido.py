from trezor import utils

if utils.UI_LAYOUT == "BOLT":
    from .bolt.fido import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "CAESAR":
    from .caesar.fido import *  # noqa: F401,F403
elif utils.UI_LAYOUT == "DELIZIA":
    from .delizia.fido import *  # noqa: F401,F403
