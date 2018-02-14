async def layout_apply_flags(ctx, msg):
    from trezor.messages.Success import Success
    from ..common import storage

    storage.set_flags(msg.flags)

    return Success(message='Flags applied')
