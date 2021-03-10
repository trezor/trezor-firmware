import storage
from trezor.messages.Success import Success
from trezor.ui.layouts import confirm_wipe

from .apply_settings import reload_settings_from_storage


async def wipe_device(ctx, msg):
    await confirm_wipe(ctx)

    storage.wipe()
    reload_settings_from_storage()

    return Success(message="Device wiped")
