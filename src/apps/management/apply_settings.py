from trezor import ui, wire
from trezor.messages import ButtonRequestType, FailureType
from trezor.messages.Success import Success
from trezor.ui.text import Text
from apps.common import storage
from apps.common.confirm import require_confirm


async def apply_settings(ctx, msg):
    if msg.homescreen is None and msg.label is None and msg.use_passphrase is None:
        raise wire.FailureError(FailureType.ProcessError, 'No setting provided')

    if msg.homescreen is not None:
        await require_confirm(ctx, Text(
            'Change homescreen', ui.ICON_CONFIG,
            'Do you really want to', 'change homescreen?'),
            code=ButtonRequestType.ProtectCall)

    # TODO: split label (bold) and '?' (normal) once we support mixed styles on one line
    if msg.label is not None:
        await require_confirm(ctx, Text(
            'Change label', ui.ICON_CONFIG,
            'Do you really want to', 'change label to',
            ui.BOLD, '%s?' % msg.label),
            code=ButtonRequestType.ProtectCall)

    if msg.use_passphrase is not None:
        await require_confirm(ctx, Text(
            'Enable passphrase' if msg.use_passphrase else 'Disable passphrase',
            ui.ICON_CONFIG,
            'Do you really want to',
            'enable passphrase' if msg.use_passphrase else 'disable passphrase',
            'encryption?'),
            code=ButtonRequestType.ProtectCall)

    storage.load_settings(label=msg.label,
                          use_passphrase=msg.use_passphrase,
                          homescreen=msg.homescreen)

    return Success(message='Settings applied')
