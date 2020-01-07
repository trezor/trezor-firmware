import storage
from trezor import io, wire
from trezor.messages.Success import Success
from trezor.sdappdata import SdAppData

if False:
    from trezor.messages.SdAppDataDelete import SdAppDataDelete


async def sd_appdata_delete(ctx: wire.Context, msg: SdAppDataDelete) -> Success:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not io.SDCard().present():
        raise wire.ProcessError("SD card not inserted")
    with SdAppData(msg.app) as appdata:
        appdata.delete(msg.key)
    return Success(message="OK")
