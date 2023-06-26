from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success
    from trezor.messages import ApplyFlags


async def apply_flags(msg: ApplyFlags) -> Success:
    import storage.device
    from storage.device import set_flags
    from trezor.wire import NotInitialized
    from trezor.messages import Success

    if not storage.device.is_initialized():
        raise NotInitialized("Device is not initialized")
    set_flags(msg.flags)
    return Success(message="Flags applied")
