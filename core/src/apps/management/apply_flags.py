from typing import TYPE_CHECKING

import storage
from trezor import wire
from trezor.messages import Success

if TYPE_CHECKING:
    from trezor.messages import ApplyFlags


async def apply_flags(ctx: wire.GenericContext, msg: ApplyFlags) -> Success:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    storage.device.set_flags(msg.flags)
    return Success(message="Flags applied")
