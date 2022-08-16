from trezor import utils

from apps.base import lock_device

# Importing homescreen for specific model,
# so that we save space in the binary.
if utils.MODEL in ("1",):
    from .t1 import Homescreen
elif utils.MODEL in ("R",):
    from .tr import Homescreen
elif utils.MODEL in ("T",):
    from .tt import Homescreen
else:
    raise ValueError("Unknown Trezor model")


async def homescreen() -> None:
    """Is model-specific - handled by import above."""
    await Homescreen()
    lock_device()
