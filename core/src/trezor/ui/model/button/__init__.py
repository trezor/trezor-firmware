from trezor import utils

if False:
    from typing import TYPE_CHECKING
else:
    TYPE_CHECKING = False

if utils.MODEL == "1":
    from .t1 import *  # noqa: F401,F403

elif utils.MODEL == "T":
    # FIXME: without the condition mypy complains about Incompatible import
    if not TYPE_CHECKING:
        from .tt import *  # noqa: F401,F403

else:
    raise ValueError("Unknown Trezor model")
