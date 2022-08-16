from trezor import utils, wire

# Importing lockscreen for specific model,
# so that we save space in the binary.
if utils.MODEL in ("1",):
    from .t1 import Lockscreen
elif utils.MODEL in ("R",):
    from .tr import Lockscreen
elif utils.MODEL in ("T",):
    from .tt import Lockscreen
else:
    raise ValueError("Unknown Trezor model")


async def lockscreen() -> None:
    """Is model-specific - handled by import above."""
    from apps.common.request_pin import can_lock_device
    from apps.base import unlock_device

    # Only show the lockscreen UI if the device can in fact be locked.
    if can_lock_device():
        await Lockscreen()
    # Otherwise proceed directly to unlock() call. If the device is already unlocked,
    # it should be a no-op storage-wise, but it resets the internal configuration
    # to an unlocked state.
    try:
        await unlock_device()
    except wire.PinCancelled:
        pass
