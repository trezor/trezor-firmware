from trezor import loop
from trezor.ui.pin import CANCELLED, PinDialog

if __debug__:
    from apps.debug import input_signal


class PinCancelled(Exception):
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
            result = await loop.race(dialog, input_signal())
        else:
            result = await dialog
        if result is CANCELLED:
            raise PinCancelled
        return result
