from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Awaitable
    from trezor.wire import Context

    from trezor.messages import ChangeWipeCode, Success


async def change_wipe_code(ctx: Context, msg: ChangeWipeCode) -> Success:
    from storage.device import is_initialized
    from trezor.wire import NotInitialized
    from trezor.ui.layouts import show_success
    from trezor.messages import Success
    from trezor import config
    from apps.common.request_pin import (
        error_pin_invalid,
        request_pin_and_sd_salt,
    )

    if not is_initialized():
        raise NotInitialized("Device is not initialized")

    # Confirm that user wants to set or remove the wipe code.
    has_wipe_code = config.has_wipe_code()
    await _require_confirm_action(ctx, msg, has_wipe_code)

    # Get the unlocking PIN.
    pin, salt = await request_pin_and_sd_salt(ctx, "Enter PIN")

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
    ctx: Context, msg: ChangeWipeCode, has_wipe_code: bool
) -> Awaitable[None]:
    from trezor.wire import ProcessError
    from trezor.ui.layouts import confirm_action

    if msg.remove and has_wipe_code:
        return confirm_action(
            ctx,
            "disable_wipe_code",
            "Disable wipe code",
            "disable wipe code protection?",
            "Do you really want to",
            reverse=True,
        )

    if not msg.remove and has_wipe_code:
        return confirm_action(
            ctx,
            "change_wipe_code",
            "Change wipe code",
            "change the wipe code?",
            "Do you really want to",
            reverse=True,
        )

    if not msg.remove and not has_wipe_code:
        return confirm_action(
            ctx,
            "set_wipe_code",
            "Set wipe code",
            "set the wipe code?",
            "Do you really want to",
            reverse=True,
        )

    # Removing non-existing wipe code.
    raise ProcessError("Wipe code protection is already disabled")


async def _request_wipe_code_confirm(ctx: Context, pin: str) -> str:
    from trezor.ui.layouts import show_popup
    from apps.common.request_pin import request_pin

    while True:
        code1 = await request_pin(ctx, "Enter new wipe code")
        if code1 == pin:
            # _wipe_code_invalid
            await show_popup(
                "Invalid wipe code",
                "The wipe code must be different from your PIN.\n\nPlease try again.",
            )
            continue

        code2 = await request_pin(ctx, "Re-enter new wipe code")
        if code1 == code2:
            return code1
        # _wipe_code_mismatch
        await show_popup(
            "Code mismatch",
            "The wipe codes you entered do not match.\n\nPlease try again.",
        )
