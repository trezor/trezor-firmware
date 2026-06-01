from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import SetBrightness, Success


async def set_brightness(msg: SetBrightness) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import set_brightness

    from apps.common.seed import raise_if_not_initialized

    raise_if_not_initialized()

    await set_brightness(msg.value)
    return Success(message="Settings applied")
