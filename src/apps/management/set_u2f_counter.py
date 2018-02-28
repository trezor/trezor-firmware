from trezor import ui, wire
from trezor.messages import ButtonRequestType, FailureType
from trezor.messages.Success import Success
from trezor.ui.text import Text
from apps.common import storage
from apps.common.confirm import require_confirm


async def set_u2f_counter(ctx, msg):
    if msg.u2f_counter is None:
        raise wire.FailureError(FailureType.ProcessError, 'No value provided provided')

    await require_confirm(ctx, Text(
        'Set U2F counter', ui.ICON_CONFIG,
        'Do you really want to',
        'set the U2F counter',
        ui.BOLD, 'to %d?' % msg.u2f_counter),
        code=ButtonRequestType.ProtectCall)

    storage.set_u2f_counter(msg.u2f_counter)

    return Success(message='U2F counter set')
