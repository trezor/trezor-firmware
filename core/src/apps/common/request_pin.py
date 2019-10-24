from trezor import config, loop, ui, wire
from trezor.messages import ButtonRequestType
from trezor.messages.ButtonAck import ButtonAck
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.pin import pin_to_int
from trezor.ui.pin import CANCELLED, PinDialog
from trezor.ui.popup import Popup
from trezor.ui.text import Text

from apps.common.sd_salt import request_sd_salt
from apps.common.storage import device

if False:
    from typing import Any, Optional, Tuple

if __debug__:
    from apps.debug import input_signal


class PinCancelled(Exception):
    pass


class PinInvalid(Exception):
    pass


async def request_pin(
    prompt: str = "Enter your PIN",
    attempts_remaining: int = None,
    allow_cancel: bool = True,
) -> str:
    if attempts_remaining is None:
        subprompt = None
    elif attempts_remaining == 1:
        subprompt = "This is your last attempt"
    else:
        subprompt = "%s attempts remaining" % attempts_remaining

    dialog = PinDialog(prompt, subprompt, allow_cancel)

    while True:
        if __debug__:
            pin = await loop.race(dialog, input_signal())
        else:
            pin = await dialog
        if pin is CANCELLED:
            raise PinCancelled
        assert isinstance(pin, str)
        return pin


async def request_pin_ack(ctx: wire.Context, *args: Any, **kwargs: Any) -> str:
    try:
        await ctx.call(ButtonRequest(code=ButtonRequestType.Other), ButtonAck)
        pin = await ctx.wait(request_pin(*args, **kwargs))
        assert isinstance(pin, str)
        return pin
    except PinCancelled:
        raise wire.ActionCancelled("Cancelled")


async def request_pin_confirm(ctx: wire.Context, *args: Any, **kwargs: Any) -> str:
    while True:
        pin1 = await request_pin_ack(ctx, "Enter new PIN", *args, **kwargs)
        pin2 = await request_pin_ack(ctx, "Re-enter new PIN", *args, **kwargs)
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
    salt_auth_key = device.get_sd_salt_auth_key()
    if salt_auth_key is not None:
        salt = await request_sd_salt(ctx, salt_auth_key)  # type: Optional[bytearray]
    else:
        salt = None

    if config.has_pin():
        pin = await request_pin_ack(ctx, prompt, config.get_pin_rem(), allow_cancel)
    else:
        pin = ""

    return pin, salt


async def verify_user_pin(
    prompt: str = "Enter your PIN", allow_cancel: bool = True, retry: bool = True
) -> None:
    salt_auth_key = device.get_sd_salt_auth_key()
    if salt_auth_key is not None:
        salt = await request_sd_salt(None, salt_auth_key)  # type: Optional[bytearray]
    else:
        salt = None

    if not config.has_pin() and not config.check_pin(pin_to_int(""), salt):
        raise RuntimeError

    while retry:
        pin = await request_pin(prompt, config.get_pin_rem(), allow_cancel)
        if config.check_pin(pin_to_int(pin), salt):
            return
        else:
            prompt = "Wrong PIN, enter again"

    raise PinInvalid


async def show_pin_invalid(ctx: wire.Context) -> None:
    from apps.common.confirm import confirm

    text = Text("Wrong PIN", ui.ICON_WRONG, ui.RED)
    text.normal("The PIN you entered is", "invalid.")
    await confirm(ctx, text, confirm=None, cancel="Close")
