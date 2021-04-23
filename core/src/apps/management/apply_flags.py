import storage.device
from storage.device import set_flags
from trezor import wire
from trezor.messages import Success


async def apply_flags(ctx, msg):
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    set_flags(msg.flags)
    return Success(message="Flags applied")
