from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.messages import WipeDevice, Success


async def wipe_device(ctx: GenericContext, msg: WipeDevice) -> Success:
    import storage
    from trezor import ui
    from trezor.enums import ButtonRequestType
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    from apps.base import reload_settings_from_storage

    await confirm_action(
        ctx,
        "confirm_wipe",
        "Wipe device",
        "All data will be lost.",
        "Do you really want to\nwipe the device?\n",
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
