from trezor import res, ui, wire

async def request_passphrase(ctx):
    from trezor.ui.text import Text
    from trezor.ui.entry_select import EntrySelector

    ui.display.clear()
    text = Text(
        'Enter passphrase', ui.ICON_RESET,
        'Where to enter your', 'passphrase?')
    entry = EntrySelector(text)
    entry_type = await entry

    on_device = on_device=(entry_type == 0)

    from trezor.messages.FailureType import ActionCancelled, ProcessError
    from trezor.messages.PassphraseRequest import PassphraseRequest
    from trezor.messages.wire_types import PassphraseAck, Cancel

    ui.display.clear()

    pass_req = PassphraseRequest()

    if on_device:
        pass_req.on_device = True
    else:
        from trezor.ui.text import Text
        text = Text(
            'Passphrase entry', ui.ICON_RESET,
            'Please, type passphrase', 'on connected host.')
        text.render()

    ack = await ctx.call(pass_req, PassphraseAck, Cancel)
    if ack.MESSAGE_WIRE_TYPE == Cancel:
        raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')

    if on_device:
        if ack.passphrase is not None:
            raise wire.FailureError(ProcessError, 'Passphrase provided when it should not be')
        from trezor.ui.passphrase import PassphraseKeyboard, CANCELLED
        passphrase = await PassphraseKeyboard('Enter passphrase')
        if passphrase == CANCELLED:
            raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')
    else:
        if ack.passphrase is None:
            raise wire.FailureError(ProcessError, 'Passphrase not provided')
        passphrase = ack.passphrase

    # TODO: process ack.state and check against the current device state, throw error if different

    return passphrase

async def protect_by_passphrase(ctx):
    from apps.common import storage

    if storage.has_passphrase():
        return await request_passphrase(ctx)
    else:
        return ''
