from trezor.messages import ZcashFullViewingKey, ZcashGetFullViewingKey

if False:
    from trezor.wire import Context

async def get_fvk(ctx: Context, msg: ZcashGetFullViewingKey) -> ZcashFullViewingKey:
    raise NotImplementedError