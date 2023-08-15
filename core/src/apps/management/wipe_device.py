from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WipeDevice


async def wipe_device(msg: WipeDevice) -> Success:
    import storage
    from trezor.enums import ButtonRequestType
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    from apps.base import reload_settings_from_storage

    await confirm_action(
        "confirm_wipe",
        "Wipe device",
        "All data will be erased.",
        "Do you really want to wipe the device?\n",
        reverse=True,
        verb="Hold to confirm",
        hold=True,
        hold_danger=True,
        br_code=ButtonRequestType.WipeDevice,
    )

    storage.wipe()
    reload_settings_from_storage()

    return Success(message="Device wiped")
