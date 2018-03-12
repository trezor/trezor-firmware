from trezor import ui, wire
from trezor.messages import ButtonRequestType, FailureType, PassphraseSourceType
from trezor.messages.Success import Success
from trezor.ui.text import Text
from apps.common import storage
from apps.common.confirm import require_confirm


async def apply_settings(ctx, msg):
    if msg.homescreen is None and msg.label is None and msg.use_passphrase is None and msg.passphrase_source is None:
        raise wire.FailureError(FailureType.ProcessError, 'No setting provided')

    if msg.homescreen is not None:
        if len(msg.homescreen) > storage.HOMESCREEN_MAXSIZE:
            raise wire.FailureError(FailureType.DataError, 'Homescreen is too complex')
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

    if msg.passphrase_source is not None:
        if msg.passphrase_source == PassphraseSourceType.DEVICE:
            desc = 'ON DEVICE'
        elif msg.passphrase_source == PassphraseSourceType.HOST:
            desc = 'ON HOST'
        else:
            desc = 'ASK'
        await require_confirm(ctx, Text(
            'Passphrase source', ui.ICON_CONFIG,
            'Do you really want to', 'change the passphrase', 'source to',
            ui.BOLD, 'ALWAYS %s?' % desc),
            code=ButtonRequestType.ProtectCall)

    storage.load_settings(label=msg.label,
                          use_passphrase=msg.use_passphrase,
                          homescreen=msg.homescreen,
                          passphrase_source=msg.passphrase_source)

    return Success(message='Settings applied')
