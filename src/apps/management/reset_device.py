from micropython import const
from trezor import wire, ui
from trezor.ui.container import Container
from trezor.utils import unimport, chunks
import ubinascii

if __debug__:
    internal_entropy = None
    current_word = None


@unimport
async def layout_reset_device(session_id, msg):
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
            FailureType.Other, 'Invalid strength (has to be 128, 192 or 256 bits)')

    if storage.is_initialized():
        raise wire.FailureError(
            FailureType.UnexpectedMessage, 'Already initialized')

    internal_entropy = random.bytes(32)

    if msg.display_random:
        entropy_lines = chunks(ubinascii.hexlify(internal_entropy), 16)
        entropy_content = Text('Internal entropy', ui.ICON_RESET, *entropy_lines)
        await require_confirm(session_id, entropy_content, ButtonRequestType.ResetDevice)

    if msg.pin_protection:
        pin = await request_pin_twice(session_id)
    else:
        pin = None

    external_entropy_ack = await wire.call(session_id, EntropyRequest(), EntropyAck)
    ctx = hashlib.sha256()
    ctx.update(internal_entropy)
    ctx.update(external_entropy_ack.entropy)
    entropy = ctx.digest()
    mnemonic = bip39.from_data(entropy[:msg.strength // 8])

    await show_mnemonic_by_word(session_id, mnemonic)

    storage.load_mnemonic(mnemonic)
    storage.load_settings(pin=pin,
                          passphrase_protection=msg.passphrase_protection,
                          language=msg.language,
                          label=msg.label)

    return Success(message='Initialized')


async def show_mnemonic_by_word(session_id, mnemonic):
    from trezor.ui.text import Text, RecoveryWordText
    from trezor.messages.ButtonRequestType import ConfirmWord
    from apps.common.confirm import confirm

    words = mnemonic.split()

    if __debug__:
        global current_word

    for index, word in enumerate(words):
        current_word = word
        content = Container(
            Text('Recovery seed setup', ui.ICON_RESET, 'Write down seed word'),
            RecoveryWordText(index + 1, word))
        await confirm(session_id,
                      content,
                      ConfirmWord)

    for index, word in enumerate(words):
        current_word = word
        content = Container(
            Text('Recovery seed setup', ui.ICON_RESET, 'Confirm seed word'),
            RecoveryWordText(index + 1, word))
        await confirm(session_id,
                      content,
                      ConfirmWord)


async def show_mnemonic(mnemonic):
    from trezor.ui.scroll import paginate

    first_page = const(0)
    words_per_page = const(4)
    words = list(enumerate(mnemonic.split()))
    pages = list(chunks(words, words_per_page))
    await paginate(show_mnemonic_page, len(pages), first_page, pages)


async def show_mnemonic_page(page, page_count, mnemonic):
    from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
    from trezor.ui.scroll import render_scrollbar, animate_swipe

    ui.display.clear()
    ui.header('Write down your seed', ui.ICON_RESET, ui.BLACK, ui.LIGHT_GREEN)
    render_scrollbar(page, page_count)

    for pi, (wi, word) in enumerate(mnemonic[page]):
        top = pi * 35 + 68
        pos = wi + 1
        offset = 0
        if pos > 9:
            offset += 12
        ui.display.text(
            10, top, '%d.' % pos, ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
        ui.display.text(
            30 + offset, top, '%s' % word, ui.BOLD, ui.WHITE, ui.BLACK)

    if page + 1 == page_count:
        await Button(
            (0, 240 - 48, 240, 48), 'Finish',
            normal_style=CONFIRM_BUTTON,
            active_style=CONFIRM_BUTTON_ACTIVE)
    else:
        await animate_swipe()
