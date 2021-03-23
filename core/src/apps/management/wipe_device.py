import storage
from trezor import ui
from trezor.enums import ButtonRequestType
from trezor.messages import Success
from trezor.ui.layouts import confirm_action

from .apply_settings import reload_settings_from_storage


async def wipe_device(ctx, msg):
    await confirm_action(
        ctx,
        "confirm_wipe",
        title="Wipe device",
        description="Do you really want to\nwipe the device?\n",
        action="All data will be lost.",
        reverse=True,
        verb="Hold to confirm",
        hold=True,
        hold_danger=True,
        icon=ui.ICON_WIPE,
        icon_color=ui.RED,
        br_code=ButtonRequestType.WipeDevice,
    )

    storage.wipe()
    reload_settings_from_storage()

    return Success(message="Device wiped")
