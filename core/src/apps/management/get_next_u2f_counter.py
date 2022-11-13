from typing import TYPE_CHECKING

from . import text_r

if TYPE_CHECKING:
    from trezor.messages import GetNextU2FCounter, NextU2FCounter
    from trezor.wire import Context


async def get_next_u2f_counter(ctx: Context, msg: GetNextU2FCounter) -> NextU2FCounter:
    import storage.device as storage_device
    from trezor.wire import NotInitialized
    from trezor.enums import ButtonRequestType
    from trezor.messages import NextU2FCounter
    from trezor.ui.layouts import confirm_action

    if not storage_device.is_initialized():
        raise NotInitialized("Device is not initialized")

    await confirm_action(
        ctx,
        "get_u2f_counter",
        "Get next U2F counter",
        description=text_r(
            "Do you really want to increase and retrieve\nthe U2F counter?"
        ),
        br_code=ButtonRequestType.ProtectCall,
    )

    return NextU2FCounter(u2f_counter=storage_device.next_u2f_counter())
