from storage.device import is_initialized
from trezor import config, ui, wire
from trezor.messages import Success
from trezor.ui.components.tt.text import Text
from trezor.ui.layouts import show_success
from trezor.ui.popup import Popup

from apps.common.confirm import require_confirm
from apps.common.request_pin import (
    error_pin_invalid,
    request_pin,
    request_pin_and_sd_salt,
)

if False:
    from trezor.messages import ChangeWipeCode


async def change_wipe_code(ctx: wire.Context, msg: ChangeWipeCode) -> Success:
    if not is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    # Confirm that user wants to set or remove the wipe code.
    has_wipe_code = config.has_wipe_code()
    await _require_confirm_action(ctx, msg, has_wipe_code)

    # Get the unlocking PIN.
    pin, salt = await request_pin_and_sd_salt(ctx)

    if not msg.remove:
        # Pre-check the entered PIN.
        if config.has_pin() and not config.check_pin(pin, salt):
            await error_pin_invalid(ctx)

        # Get new wipe code.
        wipe_code = await _request_wipe_code_confirm(ctx, pin)
    else:
        wipe_code = ""

    # Write into storage.
    if not config.change_wipe_code(pin, salt, wipe_code):
        await error_pin_invalid(ctx)

    if wipe_code:
        if has_wipe_code:
            msg_screen = "You have successfully changed the wipe code."
            msg_wire = "Wipe code changed"
        else:
            msg_screen = "You have successfully set the wipe code."
            msg_wire = "Wipe code set"
    else:
        msg_screen = "You have successfully disabled the wipe code."
        msg_wire = "Wipe code removed"

    await show_success(ctx, "success_wipe_code", msg_screen)
    return Success(message=msg_wire)


def _require_confirm_action(
    ctx: wire.Context, msg: ChangeWipeCode, has_wipe_code: bool
) -> None:
    if msg.remove and has_wipe_code:
        text = Text("Disable wipe code", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("disable wipe code")
        text.bold("protection?")
        return require_confirm(ctx, text)

    if not msg.remove and has_wipe_code:
        text = Text("Change wipe code", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("change the wipe code?")
        return require_confirm(ctx, text)

    if not msg.remove and not has_wipe_code:
        text = Text("Set wipe code", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("set the wipe code?")
        return require_confirm(ctx, text)

    # Removing non-existing wipe code.
    raise wire.ProcessError("Wipe code protection is already disabled")


async def _request_wipe_code_confirm(ctx: wire.Context, pin: str) -> str:
    while True:
        code1 = await request_pin(ctx, "Enter new wipe code")
        if code1 == pin:
            await _wipe_code_invalid()
            continue

        code2 = await request_pin(ctx, "Re-enter new wipe code")
        if code1 == code2:
            return code1
        await _wipe_code_mismatch()


async def _wipe_code_invalid() -> None:
    text = Text("Invalid wipe code", ui.ICON_WRONG, ui.RED)
    text.normal("The wipe code must be", "different from your PIN.")
    text.normal("")
    text.normal("Please try again.")
    popup = Popup(text, 3000)  # show for 3 seconds
    await popup


async def _wipe_code_mismatch() -> None:
    text = Text("Code mismatch", ui.ICON_WRONG, ui.RED)
    text.normal("The wipe codes you", "entered do not match.")
    text.normal("")
    text.normal("Please try again.")
    popup = Popup(text, 3000)  # show for 3 seconds
    await popup
