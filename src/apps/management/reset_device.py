from micropython import const
from trezor import config, ui, wire
from trezor.crypto import bip39, hashlib, random
from trezor.messages import ButtonRequestType, FailureType, wire_types
from trezor.messages.ButtonRequest import ButtonRequest
from trezor.messages.EntropyRequest import EntropyRequest
from trezor.messages.Success import Success
from trezor import workflow
from trezor.pin import pin_to_int
from trezor.ui.confirm import HoldToConfirmDialog
from trezor.ui.mnemonic import MnemonicKeyboard
from trezor.ui.scroll import Scrollpage, animate_swipe, paginate
from trezor.ui.text import Text
from trezor.utils import chunks, format_ordinal
from ubinascii import hexlify
from apps.common import storage
from apps.common.confirm import require_confirm
from apps.management.change_pin import request_pin_confirm

if __debug__:
    internal_entropy = None
    current_word = None


async def reset_device(ctx, msg):
    if __debug__:
        global internal_entropy

    # validate parameters and device state
    if msg.strength not in (128, 192, 256):
        raise wire.FailureError(
            FailureType.ProcessError,
            'Invalid strength (has to be 128, 192 or 256 bits)')
    if storage.is_initialized():
        raise wire.FailureError(
            FailureType.UnexpectedMessage,
            'Already initialized')

    if msg.pin_protection:
        # request new PIN
        newpin = await request_pin_confirm(ctx)
    else:
        # new PIN is empty
        newpin = ''

    # generate and display internal entropy
    internal_entropy = random.bytes(32)
    if msg.display_random:
        await show_entropy(ctx, internal_entropy)

    # request external entropy and compute mnemonic
    ack = await ctx.call(EntropyRequest(), wire_types.EntropyAck)
    mnemonic = generate_mnemonic(
        msg.strength, internal_entropy, ack.entropy)

    if msg.skip_backup:
        # let user backup the mnemonic later
        pass
    else:
        # warn user about mnemonic safety
        await show_warning(ctx)
        while True:
            # show mnemonic and require confirmation of a random word
            await show_mnemonic(ctx, mnemonic)
            if await check_mnemonic(ctx, mnemonic):
                break
            await show_wrong_entry(ctx)

    # write PIN into storage
    if not config.change_pin(pin_to_int(''), pin_to_int(newpin), None):
        raise wire.FailureError(
            FailureType.ProcessError, 'Could not change PIN')

    # write settings and mnemonic into storage
    storage.load_settings(
        label=msg.label, use_passphrase=msg.passphrase_protection)
    storage.load_mnemonic(
        mnemonic=mnemonic, needs_backup=msg.skip_backup)

    # show success message
    if not msg.skip_backup:
        await show_success(ctx)
    else:
        # trigger reload of homescreen
        workflow.restartdefault()

    return Success(message='Initialized')


def generate_mnemonic(strength: int,
                      int_entropy: bytes,
                      ext_entropy: bytes) -> bytes:
    ehash = hashlib.sha256()
    ehash.update(int_entropy)
    ehash.update(ext_entropy)
    entropy = ehash.digest()
    mnemonic = bip39.from_data(entropy[:strength // 8])
    return mnemonic


async def show_warning(ctx):
    content = Text(
        'Backup your seed', ui.ICON_NOCOPY,
        'Never make a digital',
        'copy of your recovery',
        'seed and never upload',
        'it online!')
    await require_confirm(
        ctx,
        content,
        ButtonRequestType.ResetDevice,
        confirm='I understand',
        cancel=None)


async def show_wrong_entry(ctx):
    content = Text(
        'Wrong entry!', ui.ICON_WRONG,
        'You have entered',
        'wrong seed word.',
        'Please check again.', icon_color=ui.RED)
    await require_confirm(
        ctx,
        content,
        ButtonRequestType.ResetDevice,
        confirm='Check again',
        cancel=None)


async def show_success(ctx):
    content = Text(
        'Backup is done!', ui.ICON_CONFIRM,
        'Never make a digital',
        'copy of your recovery',
        'seed and never upload',
        'it online!', icon_color=ui.GREEN)
    await require_confirm(
        ctx,
        content,
        ButtonRequestType.ResetDevice,
        confirm='Finish setup',
        cancel=None)


async def show_entropy(ctx, entropy: int):
    estr = hexlify(entropy).decode()
    lines = chunks(estr, 16)
    content = Text('Internal entropy', ui.ICON_RESET, ui.MONO, *lines)
    await require_confirm(
        ctx,
        content,
        ButtonRequestType.ResetDevice)


async def show_mnemonic(ctx, mnemonic: str):
    await ctx.call(
        ButtonRequest(code=ButtonRequestType.ResetDevice), wire_types.ButtonAck)
    first_page = const(0)
    words_per_page = const(4)
    words = list(enumerate(mnemonic.split()))
    pages = list(chunks(words, words_per_page))
    paginator = paginate(show_mnemonic_page, len(pages), first_page, pages)
    await ctx.wait(paginator)


@ui.layout
async def show_mnemonic_page(page: int, page_count: int, pages: list):
    lines = ['%2d. %s' % (wi + 1, word) for wi, word in pages[page]]
    content = Text('Recovery seed', ui.ICON_RESET, ui.MONO, *lines)
    content = Scrollpage(content, page, page_count)

    if page + 1 == page_count:
        await HoldToConfirmDialog(content)
    else:
        content.render()
        await animate_swipe()


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


@ui.layout
async def check_word(ctx, words: list, index: int):
    keyboard = MnemonicKeyboard('Type the %s word:' % format_ordinal(index + 1))
    result = await ctx.wait(keyboard)
    return result == words[index]
