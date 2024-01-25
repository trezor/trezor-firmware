from typing import TYPE_CHECKING

from trezor import TR

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import ChangeWipeCode, Success


async def change_wipe_code(msg: ChangeWipeCode) -> Success:
    from storage.device import is_initialized
    from trezor import config
    from trezor.messages import Success
    from trezor.ui.layouts import show_success
    from trezor.wire import NotInitialized

    from apps.common.request_pin import error_pin_invalid, request_pin_and_sd_salt

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    # Confirm that user wants to set or remove the wipe code.
    has_wipe_code = config.has_wipe_code()
    await _require_confirm_action(msg, has_wipe_code)

    # Get the unlocking PIN.
    pin, salt = await request_pin_and_sd_salt(TR.pin__enter)

    if not msg.remove:
        # Pre-check the entered PIN.
        if config.has_pin() and not config.check_pin(pin, salt):
            await error_pin_invalid()

        # Get new wipe code.
        wipe_code = await _request_wipe_code_confirm(pin)
    else:
        wipe_code = ""

    # Write into storage.
    if not config.change_wipe_code(pin, salt, wipe_code):
        await error_pin_invalid()

    if wipe_code:
        if has_wipe_code:
            msg_screen = TR.wipe_code__changed
            msg_wire = "Wipe code changed"
        else:
            msg_screen = TR.wipe_code__enabled
            msg_wire = "Wipe code set"
    else:
        msg_screen = TR.wipe_code__disabled
        msg_wire = "Wipe code removed"

    await show_success("success_wipe_code", msg_screen)
    return Success(message=msg_wire)


def _require_confirm_action(
    msg: ChangeWipeCode, has_wipe_code: bool
) -> Awaitable[None]:
    from trezor.ui.layouts import confirm_action, confirm_set_new_pin
    from trezor.wire import ProcessError

    if msg.remove and has_wipe_code:
        return confirm_action(
            "disable_wipe_code",
            TR.wipe_code__title_settings,
            description=TR.wipe_code__turn_off,
            verb=TR.buttons__turn_off,
        )

    if not msg.remove and has_wipe_code:
        return confirm_action(
            "change_wipe_code",
            TR.wipe_code__title_settings,
            description=TR.wipe_code__change,
            verb=TR.buttons__change,
        )

    if not msg.remove and not has_wipe_code:
        return confirm_set_new_pin(
            "set_wipe_code",
            TR.wipe_code__title_settings,
            TR.wipe_code__turn_on,
            TR.wipe_code__info,
        )

    # Removing non-existing wipe code.
    raise ProcessError("Wipe code protection is already disabled")


async def _request_wipe_code_confirm(pin: str) -> str:
    from trezor.ui.layouts import (
        confirm_reenter_pin,
        pin_mismatch_popup,
        wipe_code_same_as_pin_popup,
    )

    from apps.common.request_pin import request_pin

    while True:
        code1 = await request_pin(TR.wipe_code__enter_new)
        if code1 == pin:
            await wipe_code_same_as_pin_popup()
            continue
        await confirm_reenter_pin(is_wipe_code=True)
        code2 = await request_pin(TR.wipe_code__reenter)
        if code1 == code2:
            return code1
        await pin_mismatch_popup(is_wipe_code=True)
