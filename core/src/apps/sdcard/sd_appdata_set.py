import storage
from trezor import wire
from trezor.messages.Success import Success
from trezor.sdappdata import SdAppData

if False:
    from trezor.messages.SdAppDataSet import SdAppDataSet


async def sd_appdata_set(ctx: wire.Context, msg: SdAppDataSet) -> Success:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if not io.SDCard().present():
        raise wire.ProcessError("SD card not inserted")
    with SdAppData(msg.app) as appdata:
        appdata.set(msg.key, msg.value)
    return Success(message="OK")
