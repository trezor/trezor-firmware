from trezor import wire, ui
from trezor.messages.wire_types import EntropyAck
from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from trezor.ui.scroll import paginate, render_scrollbar, animate_swipe
from trezor.crypto import hashlib, random, bip39
from trezor.utils import unimport, chunks


async def generate_mnemonic(strength, display_random, session_id):
    from trezor.messages.EntropyRequest import EntropyRequest

    await wire.write_message(session_id, EntropyRequest())
    ack = await wire.read_message(session_id, EntropyAck)

    ctx = hashlib.sha256()
    ctx.update(random.bytes(32))
    ctx.update(ack.entropy)
    entropy = ctx.digest()

    # TODO: handle strength
    # TODO: handle display_random

    return bip39.from_data(entropy)


async def request_new_pin():
    from trezor.workflows.request_pin import request_pin

    pin = await request_pin()
    pin_again = await request_pin('Enter PIN again')

    if pin == pin_again:
        return pin
    else:
        raise Exception()  # TODO: wrong PIN should be handled in unified way


async def show_mnemonic(mnemonic):
    words_per_page = const(4)
    mnemonic_words = list(enumerate(mnemonic.split()))
    mnemonic_pages = list(chunks(mnemonic_words, words_per_page))

    async def render(page, page_count):

        # render header & scrollbar
        ui.clear()
        ui.display.text(10, 30, 'Write down your seed',
                        ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
        render_scrollbar(page, page_count)

        # render mnemonic page
        for pi, (wi, word) in enumerate(mnemonic_pages[page]):
            top = pi * 30 + 74
            pos = wi + 1
            ui.display.text_right(40, top, '%d.' %
                                  pos, ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
            ui.display.text(45, top, '%s' % word, ui.BOLD, ui.WHITE, ui.BLACK)

        if page + 1 == page_count:
            # wait for the finish button
            finish = Button((0, 240 - 48, 240, 48), 'Finish',
                            normal_style=CONFIRM_BUTTON,
                            active_style=CONFIRM_BUTTON_ACTIVE)
            await finish.wait()
        else:
            await animate_swipe()

    await paginate(render, len(mnemonic_pages))


async def layout_reset_device(message, session_id):
    # TODO: Failure if not empty

    mnemonic = await generate_mnemonic(
        message.strength, message.display_random, session_id)

    # if m.pin_protection:
    #     pin = yield from request_new_pin()
    # else:
    #     pin = None

    await show_mnemonic(mnemonic)
