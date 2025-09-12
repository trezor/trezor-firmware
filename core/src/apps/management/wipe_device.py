from typing import TYPE_CHECKING

from trezor import utils
from trezor.wire.context import get_context, try_get_ctx_ids

if TYPE_CHECKING:
    from trezor.messages import WipeDevice

if __debug__:
    from trezor import log


async def wipe_device(msg: WipeDevice) -> None:
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

    if __debug__:
        log.debug(__name__, "Device wipe - start")

    # start an empty progress screen so that the screen is not blank while waiting
    render_empty_loader(config.StorageMessage.PROCESSING_MSG, danger=True)

    # wipe storage
    storage.wipe(clear_cache=False)

    # clear cache - exclude current context
    storage.wipe_cache(excluded=try_get_ctx_ids())

    # erase translations
    translations.deinit()
    translations.erase()
    try:
        await get_context().write(Success(message="Device wiped"))
    except Exception:
        if __debug__:
            log.debug(__name__, "Failed to send Success message after wipe.")
        pass
    storage.wipe_cache()

    # reload settings
    reload_settings_from_storage()

    if utils.USE_BLE:
        from trezorble import erase_bonds

        # raise an exception if bonds erasing fails
        erase_bonds()

    if __debug__:
        log.debug(__name__, "Device wipe - finished")
