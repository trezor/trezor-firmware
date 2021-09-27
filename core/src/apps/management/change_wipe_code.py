from storage.device import is_initialized
from trezor import config, ui, wire
from trezor.messages import Success
from trezor.ui.layouts import confirm_action, show_popup, show_success

from apps.common.request_pin import (
    error_pin_invalid,
    request_pin,
    request_pin_and_sd_salt,
)

if False:
    from typing import Awaitable

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
) -> Awaitable[None]:
    if msg.remove and has_wipe_code:
        return confirm_action(
            ctx,
            "disable_wipe_code",
            title="Disable wipe code",
            description="Do you really want to",
            action="disable wipe code protection?",
            reverse=True,
            icon=ui.ICON_CONFIG,
        )

    if not msg.remove and has_wipe_code:
        return confirm_action(
            ctx,
            "change_wipe_code",
            title="Change wipe code",
            description="Do you really want to",
            action="change the wipe code?",
            reverse=True,
            icon=ui.ICON_CONFIG,
        )

    if not msg.remove and not has_wipe_code:
        return confirm_action(
            ctx,
            "set_wipe_code",
            title="Set wipe code",
            description="Do you really want to",
            action="set the wipe code?",
            reverse=True,
            icon=ui.ICON_CONFIG,
        )

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
    await show_popup(
        title="Invalid wipe code",
        description="The wipe code must be\ndifferent from your PIN.\n\nPlease try again.",
    )


async def _wipe_code_mismatch() -> None:
    await show_popup(
        title="Code mismatch",
        description="The wipe codes you\nentered do not match.\n\nPlease try again.",
    )
