import storage.device
from storage.device import set_flags
from trezor import wire
from trezor.messages.Success import Success

if False:
    from trezor.messages.ApplyFlags import ApplyFlags


async def apply_flags(ctx: wire.GenericContext, msg: ApplyFlags) -> Success:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if msg.flags is None:
        raise ValueError
    set_flags(msg.flags)
    return Success(message="Flags applied")
