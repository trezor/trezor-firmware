import storage
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.Success import Success
from trezor.ui.components.tt.button import ButtonCancel
from trezor.ui.components.tt.text import Text
from trezor.ui.loader import LoaderDanger

from apps.common.confirm import require_hold_to_confirm

from .apply_settings import reload_settings_from_storage


async def wipe_device(ctx, msg):
    text = Text("Wipe device", ui.ICON_WIPE, ui.RED)
    text.normal("Do you really want to", "wipe the device?", "")
    text.bold("All data will be lost.")
    await require_hold_to_confirm(
        ctx,
        text,
        ButtonRequestType.WipeDevice,
        confirm_style=ButtonCancel,
        loader_style=LoaderDanger,
    )

    storage.wipe()
    reload_settings_from_storage()

    return Success(message="Device wiped")
