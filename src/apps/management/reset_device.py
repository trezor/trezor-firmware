from micropython import const
from trezor import config, ui, wire
from trezor.utils import unimport, chunks
from ubinascii import hexlify

if __debug__:
    internal_entropy = None
    current_word = None


@unimport
async def reset_device(ctx, msg):
    from trezor.ui.text import Text
    from trezor.crypto import hashlib, random, bip39
    from trezor.ui.keyboard import MnemonicKeyboard
    from trezor.messages.EntropyRequest import EntropyRequest
    from trezor.messages.Success import Success
    from trezor.messages import FailureType
    from trezor.messages import ButtonRequestType
    from trezor.messages.wire_types import EntropyAck
    from apps.management.change_pin import request_pin_confirm
    from apps.common.confirm import require_confirm
    from apps.common import storage

    if __debug__:
        global internal_entropy

    if msg.strength not in (128, 192, 256):
        raise wire.FailureError(
            FailureType.ProcessError, 'Invalid strength (has to be 128, 192 or 256 bits)')

    if storage.is_initialized():
        raise wire.FailureError(
            FailureType.UnexpectedMessage, 'Already initialized')

    internal_entropy = random.bytes(32)

    # display internal entropy
    if msg.display_random:
        entropy_lines = chunks(hexlify(internal_entropy).decode(), 16)
        entropy_content = Text('Internal entropy', ui.ICON_RESET, ui.MONO, *entropy_lines)
        await require_confirm(ctx, entropy_content, ButtonRequestType.ResetDevice)

    # request new PIN
    if msg.pin_protection:
        curpin = ''
        newpin = await request_pin_confirm(ctx)
    else:
        curpin = ''
        newpin = ''

    # request external entropy and compute mnemonic
    external_entropy_ack = await ctx.call(EntropyRequest(), EntropyAck)
    ehash = hashlib.sha256()
    ehash.update(internal_entropy)
    ehash.update(external_entropy_ack.entropy)
    entropy = ehash.digest()
    mnemonic = bip39.from_data(entropy[:msg.strength // 8])

    # mnemonic safety warning
    warning_content = Text(
        'Backup your seed', ui.ICON_NOCOPY, ui.NORMAL,
        'Never make a digital',
        'copy of your recovery',
        'seed and never upload',
        'it online!')
    await require_confirm(
        ctx,
        warning_content,
        ButtonRequestType.ResetDevice,
        confirm='I understand',
        cancel=None)

    # ask to write down mnemonic
    await show_mnemonic(mnemonic)

    # ask for random word to check correctness
    words = mnemonic.split()
    index = random.uniform(len(words))
    res = await MnemonicKeyboard('Type %s. word' % (index + 1))
    if res != words[index]:
        content = Text(
            'Wrong entry!', ui.ICON_CLEAR,
            'You have entered',
            'wrong seed word.',
            'Please, reconnect',
            'the device and try again.', icon_color=ui.RED)
        ui.display.clear()
        await content
        raise wire.FailureError(FailureType.DataError, 'Wrong entry')

    # write into storage
    if curpin != newpin:
        config.change_pin(curpin, newpin)
    storage.load_settings(
        label=msg.label, use_passphrase=msg.passphrase_protection)
    storage.load_mnemonic(mnemonic)

    # show success message
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

    return Success(message='Initialized')


async def show_mnemonic(mnemonic):
    from trezor.ui.scroll import paginate

    first_page = const(0)
    words_per_page = const(4)
    words = list(enumerate(mnemonic.split()))
    pages = list(chunks(words, words_per_page))
    await paginate(show_mnemonic_page, len(pages), first_page, pages)


async def show_mnemonic_page(page, page_count, mnemonic):
    from trezor.ui.button import Button
    from trezor.ui.text import Text
    from trezor.ui.scroll import Scrollpage, animate_swipe

    lines = ['%d. %s' % (wi + 1, word) for wi, word in mnemonic[page]]
    scroll_page = Scrollpage(
        Text('Recovery seed setup', ui.ICON_RESET, ui.MONO, lines),
        page,
        page_count)
    ui.display.clear()
    scroll_page.render()

    if page + 1 == page_count:
        await Button(
            ui.grid(4, n_x=1),
            "I'm done",
            normal_style=ui.BTN_CONFIRM,
            active_style=ui.BTN_CONFIRM_ACTIVE)
        ui.display.clear()
    else:
        await animate_swipe()
