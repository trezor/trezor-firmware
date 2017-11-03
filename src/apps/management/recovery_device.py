from trezor import ui, wire
from trezor.utils import unimport


@unimport
async def layout_recovery_device(ctx, msg):
    from trezor.crypto import bip39
    from trezor.messages.FailureType import UnexpectedMessage, ProcessError
    from trezor.messages.Success import Success
    from trezor.ui.keyboard import KeyboardMultiTap
    from trezor.ui.text import Text
    from apps.common import storage
    from apps.common.confirm import require_confirm
    from apps.common.request_words import request_words

    if storage.is_initialized():
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    words = []

    wc = await request_words(ctx, Text(
        'Device recovery', ui.ICON_RECOVERY, 'Number of words?'))
    msg.word_count = int(wc)
    ui.display.clear()
    kbd = KeyboardMultiTap()
    for i in range(0, msg.word_count):
        kbd.prompt = 'Type %s. word' % (i + 1)
        word = await kbd
        words.append(word)

    # TODO: confirm words, start again?
    await require_confirm(ctx, Text(
        'Recovering seed', ui.ICON_RESET))

    mnemonic = ' '.join(words)

    if not msg.enforce_wordlist and not bip39.check(mnemonic):
        raise wire.FailureError(ProcessError, 'Mnemonic is not valid')

    # TODO: request pin
    pin = ''

    storage.load_mnemonic(mnemonic)
    storage.load_settings(pin=pin,
                          passphrase_protection=msg.passphrase_protection,
                          language=msg.language,
                          label=msg.label)
