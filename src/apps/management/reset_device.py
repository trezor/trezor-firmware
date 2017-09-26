from micropython import const
from trezor import wire, ui
from trezor.ui.container import Container
from trezor.utils import unimport, chunks
import ubinascii

if __debug__:
    internal_entropy = None
    current_word = None


@unimport
async def layout_reset_device(ctx, msg):
    from trezor.ui.text import Text
    from trezor.crypto import hashlib, random, bip39
    from trezor.messages.EntropyRequest import EntropyRequest
    from trezor.messages.Success import Success
    from trezor.messages import FailureType
    from trezor.messages import ButtonRequestType
    from trezor.messages.wire_types import EntropyAck

    from apps.common.request_pin import request_pin_twice
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

    if msg.display_random:
        entropy_lines = chunks(ubinascii.hexlify(internal_entropy), 16)
        entropy_content = Text('Internal entropy', ui.ICON_RESET, *entropy_lines)
        await require_confirm(ctx, entropy_content, ButtonRequestType.ResetDevice)

    if msg.pin_protection:
        pin = await request_pin_twice(ctx)
    else:
        pin = None

    external_entropy_ack = await ctx.call(EntropyRequest(), EntropyAck)
    ctx = hashlib.sha256()
    ctx.update(internal_entropy)
    ctx.update(external_entropy_ack.entropy)
    entropy = ctx.digest()
    mnemonic = bip39.from_data(entropy[:msg.strength // 8])

    await show_mnemonic_by_word(ctx, mnemonic)

    storage.load_mnemonic(mnemonic)
    storage.load_settings(pin=pin,
                          passphrase_protection=msg.passphrase_protection,
                          language=msg.language,
                          label=msg.label)

    return Success(message='Initialized')


async def show_mnemonic_by_word(ctx, mnemonic):
    from trezor.ui.text import Text
    from trezor.messages.ButtonRequestType import ConfirmWord
    from apps.common.confirm import confirm

    words = mnemonic.split()

    if __debug__:
        global current_word

    index = 0
    recovery = True

    while index < len(words):
        word = words[index]
        current_word = word
        await confirm(ctx,
                      Text(
                          'Recovery seed setup', ui.ICON_RESET,
                          ui.NORMAL, 'Write down seed word' if recovery else 'Confirm seed word', ' ',
                          ui.BOLD, '%d. %s' % (index + 1, word)),
                      ConfirmWord,
                      'Next', None)
        index += 1
        if index == len(words) and recovery:
            recovery = False
            index = 0


async def show_mnemonic(mnemonic):
    from trezor.ui.scroll import paginate

    first_page = const(0)
    words_per_page = const(4)
    words = list(enumerate(mnemonic.split()))
    pages = list(chunks(words, words_per_page))
    await paginate(show_mnemonic_page, len(pages), first_page, pages)


async def show_mnemonic_page(page, page_count, mnemonic):
    from trezor.ui.button import Button
    from trezor.ui.scroll import render_scrollbar, animate_swipe

    ui.display.clear()
    ui.header('Write down your seed', ui.ICON_RESET, ui.BG, ui.LIGHT_GREEN)
    render_scrollbar(page, page_count)

    for pi, (wi, word) in enumerate(mnemonic[page]):
        top = pi * 35 + 68
        pos = wi + 1
        offset = 0
        if pos > 9:
            offset += 12
        ui.display.text(
            10, top, '%d.' % pos, ui.BOLD, ui.LIGHT_GREEN, ui.BG)
        ui.display.text(
            30 + offset, top, '%s' % word, ui.BOLD, ui.FG, ui.BG)

    if page + 1 == page_count:
        await Button(
            (0, 240 - 48, 240, 48), 'Finish',
            normal_style=ui.BTN_CONFIRM,
            active_style=ui.BTN_CONFIRM_ACTIVE)
    else:
        await animate_swipe()
