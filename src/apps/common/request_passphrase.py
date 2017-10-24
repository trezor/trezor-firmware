from trezor import ui, wire


async def request_passphrase(ctx):
    from trezor.messages.FailureType import ActionCancelled
    from trezor.messages.PassphraseRequest import PassphraseRequest
    from trezor.messages.wire_types import PassphraseAck, Cancel
    from trezor.ui.text import Text

    ui.display.clear()
    text = Text('Enter passphrase', ui.ICON_RESET,
                'Please enter passphrase', 'on your computer.')
    text.render()

    ack = await ctx.call(PassphraseRequest(), PassphraseAck, Cancel)
    if ack.MESSAGE_WIRE_TYPE == Cancel:
        raise wire.FailureError(ActionCancelled, 'Passphrase cancelled')

    return ack.passphrase


async def protect_by_passphrase(ctx):
    from apps.common import storage

    if storage.has_passphrase():
        return await request_passphrase(ctx)
    else:
        return ''
