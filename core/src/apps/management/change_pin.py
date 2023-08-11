from typing import TYPE_CHECKING

from trezor import TR, config, wire

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import ChangePin, Success


async def change_pin(msg: ChangePin) -> Success:
    from storage.device import is_initialized
    from trezor.messages import Success
    from trezor.ui.layouts import show_success

    from apps.common.request_pin import (
        error_pin_invalid,
        error_pin_matches_wipe_code,
        request_pin_and_sd_salt,
        request_pin_confirm,
    )

    if not is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    # confirm that user wants to change the pin
    await _require_confirm_change_pin(msg)

    # get old pin
    curpin, salt = await request_pin_and_sd_salt(TR.pin__enter)

    # if changing pin, pre-check the entered pin before getting new pin
    if curpin and not msg.remove:
        if not config.check_pin(curpin, salt):
            await error_pin_invalid()

    # get new pin
    if not msg.remove:
        newpin = await request_pin_confirm()
    else:
        newpin = ""

    # write into storage
    if not config.change_pin(curpin, newpin, salt, salt):
        if newpin:
            await error_pin_matches_wipe_code()
        else:
            await error_pin_invalid()

    if newpin:
        if curpin:
            msg_screen = TR.pin__changed
            msg_wire = "PIN changed"
        else:
            msg_screen = TR.pin__enabled
            msg_wire = "PIN enabled"
    else:
        msg_screen = TR.pin__disabled
        msg_wire = "PIN removed"

    await show_success("success_pin", msg_screen)
    return Success(message=msg_wire)


def _require_confirm_change_pin(msg: ChangePin) -> Awaitable[None]:
    from trezor.ui.layouts import confirm_action, confirm_set_new_pin

    has_pin = config.has_pin()

    if msg.remove and has_pin:  # removing pin
        return confirm_action(
            "disable_pin",
            TR.pin__title_settings,
            description=TR.pin__turn_off,
            verb=TR.buttons__turn_off,
        )

    if not msg.remove and has_pin:  # changing pin
        return confirm_action(
            "change_pin",
            TR.pin__title_settings,
            description=TR.pin__change,
            verb=TR.buttons__change,
        )

    if not msg.remove and not has_pin:  # setting new pin
        return confirm_set_new_pin(
            "set_pin",
            TR.pin__title_settings,
            TR.pin__turn_on,
            TR.pin__info,
        )

    # removing non-existing PIN
    raise wire.ProcessError("PIN protection already disabled")
