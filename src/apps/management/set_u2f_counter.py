from trezor import ui, wire
from trezor.messages import ButtonRequestType
from trezor.messages.Success import Success
from trezor.ui.text import Text

from apps.common import storage
from apps.common.confirm import require_confirm


async def set_u2f_counter(ctx, msg):
    if msg.u2f_counter is None:
        raise wire.ProcessError("No value provided")

    text = Text("Set U2F counter", ui.ICON_CONFIG)
    text.normal("Do you really want to", "set the U2F counter")
    text.bold("to %d?" % msg.u2f_counter)
    await require_confirm(ctx, text, code=ButtonRequestType.ProtectCall)

    storage.set_u2f_counter(msg.u2f_counter)

    return Success(message="U2F counter set")
