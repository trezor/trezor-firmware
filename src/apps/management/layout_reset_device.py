from trezor import wire, ui
from trezor.workflows.request_pin import request_pin_repeatedly
from trezor.messages.wire_types import EntropyAck
from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from trezor.ui.scroll import paginate, render_scrollbar, animate_swipe
from trezor.crypto import hashlib, random, bip39
from trezor.utils import unimport, chunks

from .storage import get_storage, set_storage


@unimport
async def layout_reset_device(message, session_id):
    from trezor.messages.Success import Success
    from trezor.messages.Storage import Storage
    from trezor.messages.FailureType import UnexpectedMessage

    if get_storage(session_id):
        raise wire.FailureError(
            UnexpectedMessage, 'Device is already initialized')

    mnemonic = await generate_mnemonic(
        message.strength, message.display_random, session_id)

    await show_mnemonic(mnemonic)

    if message.pin_protection:
        pin = await request_pin_repeatedly(session_id)
    else:
        pin = ''

    storage = Storage(
        version=1, pin=pin, mnemonic=mnemonic,
        passphrase_protection=message.passphrase_protection,
        language=message.language, label=message.label)
    set_storage(session_id, await storage.dumps())

    return Success(message='Initialized')


@unimport
async def generate_mnemonic(strength, display_random, session_id):
    from trezor.messages.EntropyRequest import EntropyRequest
    from trezor.messages.FailureType import Other

    if strength not in (128, 192, 256):
        raise wire.FailureError(
            Other, 'Invalid strength (has to be 128, 192 or 256 bits)')

    # if display_random:
    #     raise wire.FailureError(Other, 'Entropy display not implemented')

    ack = await wire.reply_message(
        session_id, EntropyRequest(), EntropyAck)

    strength_bytes = strength // 8
    ctx = hashlib.sha256()
    ctx.update(random.bytes(strength_bytes))
    ctx.update(ack.entropy[:strength_bytes])
    entropy = ctx.digest()

    return bip39.from_data(entropy)


async def show_mnemonic(mnemonic):
    first_page = const(0)
    words_per_page = const(4)
    words = list(enumerate(mnemonic.split()))
    pages = list(chunks(words, words_per_page))
    await paginate(show_mnemonic_page, len(pages), first_page, pages)


async def show_mnemonic_page(page, page_count, mnemonic):
    ui.clear()
    ui.display.text(
        10, 30, 'Write down your seed', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    render_scrollbar(page, page_count)

    for pi, (wi, word) in enumerate(mnemonic[page]):
        top = pi * 30 + 74
        pos = wi + 1
        ui.display.text_right(
            40, top, '%d.' % pos, ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
        ui.display.text(
            45, top, '%s' % word, ui.BOLD, ui.WHITE, ui.BLACK)

    if page + 1 == page_count:
        await Button(
            (0, 240 - 48, 240, 48), 'Finish',
            normal_style=CONFIRM_BUTTON,
            active_style=CONFIRM_BUTTON_ACTIVE)
    else:
        await animate_swipe()
