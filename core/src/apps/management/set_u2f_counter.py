from typing import TYPE_CHECKING

from . import text_r

if TYPE_CHECKING:
    from trezor.messages import SetU2FCounter, Success
    from trezor.wire import Context


async def set_u2f_counter(ctx: Context, msg: SetU2FCounter) -> Success:
    import storage.device as storage_device
    from trezor import wire
    from trezor.enums import ButtonRequestType
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if msg.u2f_counter is None:
        raise wire.ProcessError("No value provided")

    await confirm_action(
        ctx,
        "set_u2f_counter",
        "Set U2F counter",
        description=text_r("Do you really want to\nset the U2F counter\nto {}?"),
        description_param=str(msg.u2f_counter),
        br_code=ButtonRequestType.ProtectCall,
    )

    storage_device.set_u2f_counter(msg.u2f_counter)

    return Success(message="U2F counter set")
