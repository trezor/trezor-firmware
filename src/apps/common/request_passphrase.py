from trezor import ui, wire


async def request_passphrase(session_id):
    from trezor.messages.PassphraseRequest import PassphraseRequest
    from trezor.messages.wire_types import PassphraseAck
    from trezor.ui.text import Text

    ui.display.clear()
    text = Text('Enter passphrase', ui.ICON_RESET,
                'Please enter passphrase', 'on your computer.')
    text.render()

    ack = await wire.reply_message(session_id, PassphraseRequest(), PassphraseAck)
    return ack.passphrase
