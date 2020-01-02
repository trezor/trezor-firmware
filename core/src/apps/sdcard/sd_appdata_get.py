import storage
from trezor import wire
from trezor.messages.SdAppDataValue import SdAppDataValue
from trezor.sdappdata import SdAppData

if False:
    from trezor.messages.SdAppDataGet import SdAppDataGet


async def sd_appdata_get(ctx: wire.Context, msg: SdAppDataGet) -> SdAppDataValue:
    if not storage.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    appdata = SdAppData(msg.app)
    value = appdata.get(msg.key)
    return SdAppDataValue(value=value)
