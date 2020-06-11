import storage.device
from storage.device import set_flags
from trezor.messages.Success import Success

import wire


async def apply_flags(ctx, msg):
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    set_flags(msg.flags)
    return Success(message="Flags applied")
