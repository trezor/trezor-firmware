from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, WipeDevice


async def wipe_device(msg: WipeDevice) -> Success:
    import storage
    from trezor import TR, config, translations
    from trezor.enums import ButtonRequestType
    from trezor.messages import Success
    from trezor.pin import render_empty_loader
    from trezor.ui.layouts import confirm_action

    from apps.base import reload_settings_from_storage

    await confirm_action(
        "confirm_wipe",
        TR.wipe__title,
        TR.wipe__info,
        TR.wipe__want_to_wipe,
        reverse=True,
        verb=TR.buttons__hold_to_confirm,
        hold=True,
        hold_danger=True,
        br_code=ButtonRequestType.WipeDevice,
    )

    # start an empty progress screen so that the screen is not blank while waiting
    render_empty_loader(config.StorageMessage.PROCESSING_MSG)

    # wipe storage
    storage.wipe()
    # erase translations
    translations.deinit()
    translations.erase()

    # reload settings
    reload_settings_from_storage()

    return Success(message="Device wiped")
