import storage
from trezor import wire
from trezor.messages.Success import Success
from trezor.sdappdata import SdAppData

if False:
    from trezor.messages.SdAppDataDelete import SdAppDataDelete


async def sd_appdata_delete(ctx: wire.Context, msg: SdAppDataDelete) -> Success:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    appdata = SdAppData(msg.app)
    appdata.delete(msg.key)
    return Success(message="OK")
