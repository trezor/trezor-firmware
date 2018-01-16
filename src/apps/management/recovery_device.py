from trezor import ui, wire


async def recovery_device(ctx, msg):
    '''
    Recover BIP39 seed into empty device.

    1. Ask for the number of words in recovered seed.
    2. Let user type in the mnemonic words one by one.
    3. Optionally check the seed validity.
    4. Optionally ask for the PIN, with confirmation.
    5. Save into storage.
    '''
    from trezor import config
    from trezor.crypto import bip39
    from trezor.messages.FailureType import UnexpectedMessage, ProcessError
    from trezor.messages.Success import Success
    from trezor.ui.text import Text
    from apps.common import storage
    from apps.common.request_pin import request_pin
    from apps.common.request_words import request_words

    if storage.is_initialized():
        raise wire.FailureError(UnexpectedMessage, 'Already initialized')

    wordcount = await request_words(ctx,
                                    Text('Device recovery', ui.ICON_RECOVERY,
                                         'Number of words?'))
    mnemonic = await request_mnemonic(wordcount, 'Type %s. word')

    if msg.enforce_wordlist and not bip39.check(mnemonic):
        raise wire.FailureError(ProcessError, 'Mnemonic is not valid')

    if msg.pin_protection:
        curpin = ''
        newpin = await request_pin(ctx)
        config.change_pin(curpin, newpin)

    storage.load_settings(label=msg.label,
                          use_passphrase=msg.passphrase_protection)
    storage.load_mnemonic(mnemonic)
    return Success()


async def request_mnemonic(count: int, prompt: str) -> str:
    from trezor.ui.keyboard import MnemonicKeyboard

    words = []
    board = MnemonicKeyboard()
    for i in range(0, count):
        board.prompt = prompt % (i + 1)
        word = await board
        words.append(word)

    return ' '.join(words)
