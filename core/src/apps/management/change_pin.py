from typing import TYPE_CHECKING

from trezor import config, wire

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import ChangePin, Success
    from trezor.wire import Context


async def change_pin(ctx: Context, msg: ChangePin) -> Success:
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
    await _require_confirm_change_pin(ctx, msg)

    # get old pin
    curpin, salt = await request_pin_and_sd_salt(ctx, "Enter PIN")

    # if changing pin, pre-check the entered pin before getting new pin
    if curpin and not msg.remove:
        if not config.check_pin(curpin, salt):
            await error_pin_invalid(ctx)

    # get new pin
    if not msg.remove:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

    # write into storage
    if not config.change_pin(curpin, newpin, salt, salt):
        if newpin:
            await error_pin_matches_wipe_code(ctx)
        else:
            await error_pin_invalid(ctx)

    if newpin:
        if curpin:
            msg_screen = "PIN changed."
            msg_wire = "PIN changed"
        else:
            msg_screen = "PIN protection enabled."
            msg_wire = "PIN enabled"
    else:
        msg_screen = "PIN protection disabled."
        msg_wire = "PIN removed"

    await show_success(ctx, "success_pin", msg_screen)
    return Success(message=msg_wire)


def _require_confirm_change_pin(ctx: Context, msg: ChangePin) -> Awaitable[None]:
    from trezor.ui.layouts import confirm_action, confirm_set_new_pin

    has_pin = config.has_pin()

    br_type = "set_pin"
    title = "PIN settings"

    if msg.remove and has_pin:  # removing pin
        return confirm_action(
            ctx,
            br_type,
            title,
            description="Do you want to disable PIN protection?",
            verb="Disable",
        )

    if not msg.remove and has_pin:  # changing pin
        return confirm_action(
            ctx,
            br_type,
            title,
            description="Do you want to change your PIN?",
            verb="Change",
        )

    if not msg.remove and not has_pin:  # setting new pin
        return confirm_set_new_pin(
            ctx,
            br_type,
            title,
            "Do you want to enable PIN protection?",
            [
                "PIN will be used to access this device.",
                "PIN should be 4-50 digits long.",
            ],
        )

    # removing non-existing PIN
    raise wire.ProcessError("PIN protection already disabled")
