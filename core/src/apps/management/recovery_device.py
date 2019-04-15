from trezor import config, ui, wire
from trezor.crypto import bip39
from trezor.crypto.hashlib import sha256
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.ButtonRequestType import (
    MnemonicInput,
    MnemonicWordCount,
    ProtectCall,
)
from trezor.messages.MessageType import ButtonAck
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.mnemonic import MnemonicKeyboard
from trezor.ui.text import Text
from trezor.ui.word_select import WordSelector
from trezor.utils import consteq, format_ordinal

from apps.common import mnemonic, storage
from apps.common.confirm import require_confirm
from apps.management.change_pin import request_pin_ack, request_pin_confirm


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

    if not msg.dry_run:
        title = "Device recovery"
        text = Text(title, ui.ICON_RECOVERY)
        text.normal("Do you really want to", "recover the device?", "")
    else:
        title = "Simulated recovery"
        text = Text(title, ui.ICON_RECOVERY)
        text.normal("Do you really want to", "check the recovery", "seed?")

    await require_confirm(ctx, text, code=ProtectCall)

    if msg.dry_run:
        if config.has_pin():
            curpin = await request_pin_ack(ctx, "Enter PIN", config.get_pin_rem())
        else:
            curpin = ""
        if not config.check_pin(pin_to_int(curpin)):
            raise wire.PinInvalid("PIN invalid")

    # ask for the number of words
    wordcount = await request_wordcount(ctx, title)

    # ask for mnemonic words one by one
    words = await request_mnemonic(ctx, wordcount)

    # check mnemonic validity
    if msg.enforce_wordlist or msg.dry_run:
        if not bip39.check(words):
            raise wire.ProcessError("Mnemonic is not valid")

    # ask for pin repeatedly
    if msg.pin_protection:
        newpin = await request_pin_confirm(ctx, cancellable=False)
    else:
        newpin = ""

    secret = mnemonic.process([words], mnemonic.TYPE_BIP39)

    # dry run
    if msg.dry_run:
        digest_input = sha256(secret).digest()
        stored, _ = mnemonic.get()
        digest_stored = sha256(stored).digest()
        if consteq(digest_stored, digest_input):
            return Success(
                message="The seed is valid and matches the one in the device"
            )
        else:
            raise wire.ProcessError(
                "The seed is valid but does not match the one in the device"
            )

    # save into storage
    if newpin:
        config.change_pin(pin_to_int(""), pin_to_int(newpin))
    storage.set_u2f_counter(msg.u2f_counter)
    storage.load_settings(label=msg.label, use_passphrase=msg.passphrase_protection)
    storage.store_mnemonic(
        secret=secret,
        mnemonic_type=mnemonic.TYPE_BIP39,
        needs_backup=False,
        no_backup=False,
    )

    return Success(message="Device recovered")


@ui.layout
async def request_wordcount(ctx, title: str) -> int:
    await ctx.call(ButtonRequest(code=MnemonicWordCount), ButtonAck)

    text = Text(title, ui.ICON_RECOVERY)
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
