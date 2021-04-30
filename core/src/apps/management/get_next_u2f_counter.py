import storage.device
from trezor import ui, wire
from trezor.messages import ButtonRequestType, GetNextU2FCounter, NextU2FCounter
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm


async def get_next_u2f_counter(
    ctx: wire.Context, msg: GetNextU2FCounter
) -> NextU2FCounter:
    if not storage.device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
    text = Text("Get next U2F counter", ui.ICON_CONFIG)
    text.normal("Do you really want to")
    text.bold("increase and retrieve")
    text.normal("the U2F counter?")
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)

    return NextU2FCounter(u2f_counter=storage.device.next_u2f_counter())
