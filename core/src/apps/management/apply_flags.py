from trezor.messages.Success import Success

from apps.common.storage.device import set_flags


async def apply_flags(ctx, msg):
    set_flags(msg.flags)
    return Success(message="Flags applied")
