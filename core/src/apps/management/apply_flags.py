from storage.device import set_flags
from trezor.messages.Success import Success


async def apply_flags(ctx, msg):
    set_flags(msg.flags)
    return Success(message="Flags applied")
