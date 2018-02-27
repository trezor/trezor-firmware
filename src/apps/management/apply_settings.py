from trezor import ui, wire


async def layout_apply_settings(ctx, msg):
    from trezor.messages.Success import Success
    from trezor.messages import ButtonRequestType, FailureType
    from trezor.ui.text import Text
    from ..common.confirm import require_confirm
    from ..common import storage

    if msg.homescreen is None and msg.label is None and msg.language is None and msg.use_passphrase is None:
        raise wire.FailureError(FailureType.ProcessError, 'No setting provided')

    if msg.homescreen is not None:
        await require_confirm(ctx, Text(
            'Change homescreen', ui.ICON_DEFAULT,
            'Do you really want to', 'change homescreen?'),
            code=ButtonRequestType.ProtectCall)

    if msg.label is not None:
        await require_confirm(ctx, Text(
            'Change label', ui.ICON_DEFAULT,
            'Do you really want to', 'change label to',
            ui.BOLD, '%s?' % msg.label),  # TODO: split label (bold) and '?' (normal) once we support mixed styles on one line
            code=ButtonRequestType.ProtectCall)

    if msg.language is not None:
        await require_confirm(ctx, Text(
            'Change language', ui.ICON_DEFAULT,
            'Do you really want to', 'change language to',
            ui.BOLD, '%s?' % msg.language),  # TODO: split lang (bold) and '?' (normal) once we support mixed styles on one line
            code=ButtonRequestType.ProtectCall)

    if msg.use_passphrase is not None:
        await require_confirm(ctx, Text(
            'Enable passphrase' if msg.use_passphrase else 'Disable passphrase',
            ui.ICON_DEFAULT,
            'Do you really want to',
            'enable passphrase' if msg.use_passphrase else 'disable passphrase',
            'encryption?'),
            code=ButtonRequestType.ProtectCall)

    storage.load_settings(label=msg.label,
                          use_passphrase=msg.use_passphrase,
                          homescreen=msg.homescreen)

    return Success(message='Settings applied')
