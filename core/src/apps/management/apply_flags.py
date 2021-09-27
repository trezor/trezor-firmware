import storage.device
from storage.device import set_flags
from trezor import wire
from trezor.messages import Success

if False:
    from trezor.messages import ApplyFlags


async def apply_flags(ctx: wire.GenericContext, msg: ApplyFlags) -> Success:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    set_flags(msg.flags)
    return Success(message="Flags applied")
