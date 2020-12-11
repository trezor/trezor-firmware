import utime

import storage.sd_salt
from trezor import config, ui, wire
from trezor.messages import ButtonRequestType
from trezor.pin import pin_to_int
from trezor.ui.components.tt.pin import CANCELLED, PinDialog
from trezor.ui.components.tt.text import Text
from trezor.ui.popup import Popup

from . import button_request
from .sdcard import SdCardUnavailable, request_sd_salt

if False:
    from typing import Any, NoReturn, Optional, Tuple


_last_successful_unlock = 0


def can_lock_device() -> bool:
    """Return True if the device has a PIN set or SD-protect enabled."""
    return config.has_pin() or storage.sd_salt.is_enabled()


async def request_pin(
    ctx: wire.GenericContext,
    prompt: str = "Enter your PIN",
    attempts_remaining: int = None,
    allow_cancel: bool = True,
) -> str:
    await button_request(ctx, code=ButtonRequestType.PinEntry)

    if attempts_remaining is None:
        subprompt = None
    elif attempts_remaining == 1:
        subprompt = "This is your last attempt"
    else:
        subprompt = "%s attempts remaining" % attempts_remaining

    dialog = PinDialog(prompt, subprompt, allow_cancel)

    while True:
        pin = await ctx.wait(dialog)
        if pin is CANCELLED:
            raise wire.PinCancelled
        assert isinstance(pin, str)
        return pin


async def request_pin_confirm(ctx: wire.Context, *args: Any, **kwargs: Any) -> str:
    while True:
        pin1 = await request_pin(ctx, "Enter new PIN", *args, **kwargs)
        pin2 = await request_pin(ctx, "Re-enter new PIN", *args, **kwargs)
        if pin1 == pin2:
            return pin1
        await pin_mismatch()


async def pin_mismatch() -> None:
    text = Text("PIN mismatch", ui.ICON_WRONG, ui.RED)
    text.normal("The PINs you entered", "do not match.")
    text.normal("")
    text.normal("Please try again.")
    popup = Popup(text, 3000)  # show for 3 seconds
    await popup


async def request_pin_and_sd_salt(
    ctx: wire.Context, prompt: str = "Enter your PIN", allow_cancel: bool = True
) -> Tuple[str, Optional[bytearray]]:
    if config.has_pin():
        pin = await request_pin(ctx, prompt, config.get_pin_rem(), allow_cancel)
        config.ensure_not_wipe_code(pin_to_int(pin))
    else:
        pin = ""

    salt = await request_sd_salt(ctx)

    return pin, salt


async def verify_user_pin(
    ctx: wire.GenericContext = wire.DUMMY_CONTEXT,
    prompt: str = "Enter your PIN",
    allow_cancel: bool = True,
    retry: bool = True,
    cache_time_ms: int = 0,
) -> None:
    global _last_successful_unlock
    if (
        cache_time_ms
        and _last_successful_unlock
        and utime.ticks_ms() - _last_successful_unlock <= cache_time_ms
        and config.is_unlocked()
    ):
        return

    if config.has_pin():
        pin = await request_pin(ctx, prompt, config.get_pin_rem(), allow_cancel)
        config.ensure_not_wipe_code(pin_to_int(pin))
    else:
        pin = ""

    try:
        salt = await request_sd_salt(ctx)
    except SdCardUnavailable:
        raise wire.PinCancelled("SD salt is unavailable")
    if config.unlock(pin_to_int(pin), salt):
        _last_successful_unlock = utime.ticks_ms()
        return
    elif not config.has_pin():
        raise RuntimeError

    while retry:
        pin = await request_pin(
            ctx, "Wrong PIN, enter again", config.get_pin_rem(), allow_cancel
        )
        if config.unlock(pin_to_int(pin), salt):
            _last_successful_unlock = utime.ticks_ms()
            return

    raise wire.PinInvalid


async def error_pin_invalid(ctx: wire.Context) -> NoReturn:
    from apps.common.confirm import confirm

    text = Text("Wrong PIN", ui.ICON_WRONG, ui.RED)
    text.normal("The PIN you entered is", "invalid.")
    await confirm(ctx, text, confirm=None, cancel="Close")
    raise wire.PinInvalid


async def error_pin_matches_wipe_code(ctx: wire.Context) -> NoReturn:
    from apps.common.confirm import confirm

    text = Text("Invalid PIN", ui.ICON_WRONG, ui.RED)
    text.normal("The new PIN must be", "different from your", "wipe code.")
    await confirm(ctx, text, confirm=None, cancel="Close")
    raise wire.PinInvalid
