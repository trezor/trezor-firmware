from micropython import const
from ubinascii import hexlify

from trezor import config, ui, wire
from trezor.crypto import bip39, hashlib, random
from trezor.messages import ButtonRequestType, MessageType
from trezor.messages.EntropyRequest import EntropyRequest
from trezor.messages.Success import Success
from trezor.pin import pin_to_int
from trezor.ui.mnemonic import MnemonicKeyboard
from trezor.ui.scroll import Paginated
from trezor.ui.text import Text
from trezor.utils import chunks, format_ordinal

from apps.common import mnemonic, storage
from apps.common.confirm import hold_to_confirm, require_confirm
from apps.management.change_pin import request_pin_confirm

if __debug__:
    from apps import debug


async def reset_device(ctx, msg):
    # validate parameters and device state
    if msg.strength not in (128, 192, 256):
        raise wire.ProcessError("Invalid strength (has to be 128, 192 or 256 bits)")
    if msg.display_random and (msg.skip_backup or msg.no_backup):
        raise wire.ProcessError("Can't show internal entropy when backup is skipped")
    if storage.is_initialized():
        raise wire.UnexpectedMessage("Already initialized")

    # make sure use knows he's setting up a new wallet
    await show_reset_warning(ctx)

    # request new PIN
    if msg.pin_protection:
        newpin = await request_pin_confirm(ctx)
    else:
        newpin = ""

    # generate and display internal entropy
    internal_ent = random.bytes(32)
    if __debug__:
        debug.reset_internal_entropy = internal_ent
    if msg.display_random:
        await show_entropy(ctx, internal_ent)

    # request external entropy and compute mnemonic
    ent_ack = await ctx.call(EntropyRequest(), MessageType.EntropyAck)
    words = generate_mnemonic(msg.strength, internal_ent, ent_ack.entropy)

    if not msg.skip_backup and not msg.no_backup:
        # require confirmation of the mnemonic safety
        await show_backup_warning(ctx)

        # show mnemonic and require confirmation of a random word
        while True:
            await show_mnemonic(ctx, words)
            if await check_mnemonic(ctx, words):
                break
            await show_wrong_entry(ctx)

    # write PIN into storage
    if newpin:
        if not config.change_pin(pin_to_int(""), pin_to_int(newpin)):
            raise wire.ProcessError("Could not change PIN")

    secret = mnemonic.process([words], mnemonic.TYPE_BIP39)
    # write settings and mnemonic into storage
    storage.load_settings(label=msg.label, use_passphrase=msg.passphrase_protection)
    storage.store_mnemonic(
        secret=secret,
        mnemonic_type=mnemonic.TYPE_BIP39,
        needs_backup=msg.skip_backup,
        no_backup=msg.no_backup,
    )

    # show success message
    if not msg.skip_backup and not msg.no_backup:
        await show_success(ctx)

    return Success(message="Initialized")


def generate_mnemonic(strength: int, int_entropy: bytes, ext_entropy: bytes) -> bytes:
    ehash = hashlib.sha256()
    ehash.update(int_entropy)
    ehash.update(ext_entropy)
    entropy = ehash.digest()
    return bip39.from_data(entropy[: strength // 8])


async def show_reset_warning(ctx):
    text = Text("Create a new wallet", ui.ICON_RESET, new_lines=False)
    text.normal("Do you really want to")
    text.br()
    text.normal("create a new wallet?")
    text.br()
    text.br_half()
    text.normal("By continuing you agree")
    text.br()
    text.normal("to")
    text.bold("https://trezor.io/tos")
    await require_confirm(ctx, text, code=ButtonRequestType.ResetDevice)


async def show_backup_warning(ctx):
    text = Text("Backup your seed", ui.ICON_NOCOPY)
    text.normal(
        "Never make a digital",
        "copy of your recovery",
        "seed and never upload",
        "it online!",
    )
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="I understand", cancel=None
    )


async def show_wrong_entry(ctx):
    text = Text("Wrong entry!", ui.ICON_WRONG, ui.RED)
    text.normal("You have entered", "wrong seed word.", "Please check again.")
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="Check again", cancel=None
    )


async def show_success(ctx):
    text = Text("Backup is done!", ui.ICON_CONFIRM, ui.GREEN)
    text.normal(
        "Never make a digital",
        "copy of your recovery",
        "seed and never upload",
        "it online!",
    )
    await require_confirm(
        ctx, text, ButtonRequestType.ResetDevice, confirm="Finish setup", cancel=None
    )


async def show_entropy(ctx, entropy: bytes):
    entropy_str = hexlify(entropy).decode()
    lines = chunks(entropy_str, 16)
    text = Text("Internal entropy", ui.ICON_RESET)
    text.mono(*lines)
    await require_confirm(ctx, text, ButtonRequestType.ResetDevice)


async def show_mnemonic(ctx, mnemonic: str):
    # split mnemonic words into pages
    PER_PAGE = const(4)
    words = mnemonic.split()
    words = list(enumerate(words))
    words = list(chunks(words, PER_PAGE))

    # display the pages, with a confirmation dialog on the last one
    pages = [get_mnemonic_page(page) for page in words]
    paginated = Paginated(pages)

    if __debug__:

        def export_displayed_words():
            # export currently displayed mnemonic words into debuglink
            debug.reset_current_words = [w for _, w in words[paginated.page]]

        paginated.on_change = export_displayed_words
        export_displayed_words()

    await hold_to_confirm(ctx, paginated, ButtonRequestType.ResetDevice)


def get_mnemonic_page(words: list):
    text = Text("Recovery seed", ui.ICON_RESET)
    for index, word in words:
        text.mono("%2d. %s" % (index + 1, word))
    return text


async def check_mnemonic(ctx, mnemonic: str) -> bool:
    words = mnemonic.split()

    # check a word from the first half
    index = random.uniform(len(words) // 2)
    if not await check_word(ctx, words, index):
        return False

    # check a word from the second half
    index = random.uniform(len(words) // 2) + len(words) // 2
    if not await check_word(ctx, words, index):
        return False

    return True


async def check_word(ctx, words: list, index: int):
    if __debug__:
        debug.reset_word_index = index
    keyboard = MnemonicKeyboard("Type the %s word:" % format_ordinal(index + 1))
    if __debug__:
        result = await ctx.wait(keyboard, debug.input_signal)
    else:
        result = await ctx.wait(keyboard)
    return result == words[index]
