from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ApplyFlags, Success
    from trezor.wire import GenericContext


async def apply_flags(ctx: GenericContext, msg: ApplyFlags) -> Success:
    import storage.device
    from storage.device import set_flags
    from trezor.messages import Success
    from trezor.wire import NotInitialized

    if not storage.device.is_initialized():
        raise NotInitialized("Device is not initialized")
    set_flags(msg.flags)
    return Success(message="Flags applied")
