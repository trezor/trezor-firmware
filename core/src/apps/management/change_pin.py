from storage.device import is_initialized
from trezor import config, ui, wire
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.components.tt.text import Text
from trezor.ui.layouts import require, show_success

from apps.common.confirm import require_confirm
from apps.common.request_pin import (
    error_pin_invalid,
    error_pin_matches_wipe_code,
    request_pin_and_sd_salt,
    request_pin_confirm,
)

if False:
    from trezor.messages.ChangePin import ChangePin


async def change_pin(ctx: wire.Context, msg: ChangePin) -> Success:
    if not is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    # confirm that user wants to change the pin
    await require_confirm_change_pin(ctx, msg)

    # get old pin
    curpin, salt = await request_pin_and_sd_salt(ctx, "Enter old PIN")

    # if changing pin, pre-check the entered pin before getting new pin
    if curpin and not msg.remove:
        if not config.check_pin(pin_to_int(curpin), salt):
            await error_pin_invalid(ctx)

    # get new pin
    if not msg.remove:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

    # write into storage
    if not config.change_pin(pin_to_int(curpin), pin_to_int(newpin), salt, salt):
        if newpin:
            await error_pin_matches_wipe_code(ctx)
        else:
            await error_pin_invalid(ctx)

    if newpin:
        if curpin:
            msg_screen = "You have successfully changed your PIN."
            msg_wire = "PIN changed"
        else:
            msg_screen = "You have successfully enabled PIN protection."
            msg_wire = "PIN enabled"
    else:
        msg_screen = "You have successfully disabled PIN protection."
        msg_wire = "PIN removed"

    await require(show_success(ctx, "success_pin", msg_screen))
    return Success(message=msg_wire)


def require_confirm_change_pin(ctx: wire.Context, msg: ChangePin) -> None:
    has_pin = config.has_pin()

    if msg.remove and has_pin:  # removing pin
        text = Text("Remove PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("disable PIN protection?")
        return require_confirm(ctx, text)

    if not msg.remove and has_pin:  # changing pin
        text = Text("Change PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("change your PIN?")
        return require_confirm(ctx, text)

    if not msg.remove and not has_pin:  # setting new pin
        text = Text("Enable PIN", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("enable PIN protection?")
        return require_confirm(ctx, text)

    # removing non-existing PIN
    raise wire.ProcessError("PIN protection already disabled")
