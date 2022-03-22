import storage.device
from trezor import ui, wire
from trezor.enums import ButtonRequestType
from trezor.messages import SetU2FCounter, Success
from trezor.ui.layouts import confirm_action


async def set_u2f_counter(ctx: wire.Context, msg: SetU2FCounter) -> Success:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    if msg.u2f_counter is None:
        raise wire.ProcessError("No value provided")

    await confirm_action(
        ctx,
        "set_u2f_counter",
        title="Set U2F counter",
        description="Do you really want to\nset the U2F counter\nto {}?",
        description_param=str(msg.u2f_counter),
        icon=ui.ICON_CONFIG,
        br_code=ButtonRequestType.ProtectCall,
    )

    storage.device.set_u2f_counter(msg.u2f_counter)

    return Success(message="U2F counter set")
