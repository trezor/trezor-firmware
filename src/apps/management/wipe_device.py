from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.messages.Success import Success
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_hold_to_confirm


async def wipe_device(ctx, msg):

    text = Text("Wipe device", ui.ICON_WIPE, icon_color=ui.RED)
    text.normal("Do you really want to", "wipe the device?", "")
    text.bold("All data will be lost.")

    await require_hold_to_confirm(
        ctx,
        text,
        code=ButtonRequestType.WipeDevice,
        button_style=ui.BTN_CANCEL,
        loader_style=ui.LDR_DANGER,
    )

    storage.wipe()

    return Success(message="Device wiped")
