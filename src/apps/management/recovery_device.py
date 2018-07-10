from trezor import config, ui, wire
from trezor.crypto import bip39
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.ButtonRequestType import MnemonicInput, MnemonicWordCount
from trezor.messages.MessageType import ButtonAck
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.mnemonic import MnemonicKeyboard
from trezor.ui.text import Text
from trezor.ui.word_select import WordSelector
from trezor.utils import format_ordinal

from apps.common import storage
from apps.management.change_pin import request_pin_confirm


async def recovery_device(ctx, msg):
    """
    Recover BIP39 seed into empty device.

    1. Ask for the number of words in recovered seed.
    2. Let user type in the mnemonic words one by one.
    3. Optionally check the seed validity.
    4. Optionally ask for the PIN, with confirmation.
    5. Save into storage.
    """
    if not msg.dry_run and storage.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")

    # ask for the number of words
    wordcount = await request_wordcount(ctx)

    # ask for mnemonic words one by one
    mnemonic = await request_mnemonic(ctx, wordcount)

    # check mnemonic validity
    if msg.enforce_wordlist or msg.dry_run:
        if not bip39.check(mnemonic):
            raise wire.ProcessError("Mnemonic is not valid")

    # ask for pin repeatedly
    if msg.pin_protection:
        newpin = await request_pin_confirm(ctx, cancellable=False)

    # save into storage
    if not msg.dry_run:
        if msg.pin_protection:
            config.change_pin(pin_to_int(""), pin_to_int(newpin), None)
        storage.load_settings(label=msg.label, use_passphrase=msg.passphrase_protection)
        storage.load_mnemonic(mnemonic=mnemonic, needs_backup=False)
        return Success(message="Device recovered")
    else:
        if storage.get_mnemonic() == mnemonic:
            return Success(
                message="The seed is valid and matches the one in the device"
            )
        else:
            raise wire.ProcessError(
                "The seed is valid but does not match the one in the device"
            )


@ui.layout
async def request_wordcount(ctx):
    await ctx.call(ButtonRequest(code=MnemonicWordCount), ButtonAck)

    text = Text("Device recovery", ui.ICON_RECOVERY)
    text.normal("Number of words?")
    count = await ctx.wait(WordSelector(text))

    return count


@ui.layout
async def request_mnemonic(ctx, count: int) -> str:
    await ctx.call(ButtonRequest(code=MnemonicInput), ButtonAck)

    words = []
    board = MnemonicKeyboard()
    for i in range(count):
        board.prompt = "Type the %s word:" % format_ordinal(i + 1)
        word = await ctx.wait(board)
        words.append(word)

    return " ".join(words)
