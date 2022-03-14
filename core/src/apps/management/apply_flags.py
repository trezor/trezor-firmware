from typing import TYPE_CHECKING

from storage.device import set_flags
from trezor import storagedevice, wire
from trezor.messages import Success

if TYPE_CHECKING:
    from trezor.messages import ApplyFlags


async def apply_flags(ctx: wire.GenericContext, msg: ApplyFlags) -> Success:
    if not storagedevice.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    set_flags(msg.flags)
    return Success(message="Flags applied")
