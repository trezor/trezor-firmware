from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import SetU2FCounter, Success


async def set_u2f_counter(msg: SetU2FCounter) -> Success:
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
        "set_u2f_counter",
        "Set U2F counter",
        description="Set the U2F counter to {}?",
        description_param=str(msg.u2f_counter),
        verb="SET",
        br_code=ButtonRequestType.ProtectCall,
    )

    storage_device.set_u2f_counter(msg.u2f_counter)

    return Success(message="U2F counter set")
