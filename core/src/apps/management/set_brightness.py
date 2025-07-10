from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import SetBrightness, Success


async def set_brightness(msg: SetBrightness) -> Success:
    import storage.device as storage_device
    from trezor.messages import Success
    from trezor.ui.layouts import set_brightness
    from trezor.wire import NotInitialized

    if not storage_device.is_initialized():
        raise NotInitialized("Device is not initialized")

    await set_brightness(msg.value)
    return Success(message="Settings applied")
