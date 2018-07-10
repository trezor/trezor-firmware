from trezor.messages.Success import Success

from apps.common import storage


async def apply_flags(ctx, msg):
    storage.set_flags(msg.flags)
    return Success(message="Flags applied")
