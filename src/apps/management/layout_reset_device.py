from trezor import wire, ui
from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from trezor.ui.scroll import paginate, render_scrollbar, animate_swipe
from trezor.crypto import hashlib, random, bip39
from trezor.utils import unimport_gen, chunks


def generate_mnemonic(strength, display_random):
    from trezor.messages.EntropyRequest import EntropyRequest
    from trezor.messages.EntropyAck import EntropyAck

    ack = yield from wire.call(EntropyRequest(), EntropyAck)

    ctx = hashlib.sha256()
    ctx.update(random.bytes(32))
    ctx.update(ack.entropy)
    entropy = ctx.digest()

    # TODO: handle strength
    # TODO: handle display_random

    return bip39.from_data(entropy)


def request_new_pin():
    from trezor.workflows.request_pin import request_pin

    pin = yield from request_pin()
    pin_again = yield from request_pin('Enter PIN again')

    if pin == pin_again:
        return pin
    else:
        raise Exception()  # TODO: wrong PIN should be handled in unified way


def show_mnemonic(mnemonic):
    words_per_page = const(4)
    mnemonic_words = list(enumerate(mnemonic.split()))
    mnemonic_pages = list(chunks(mnemonic_words, words_per_page))

    def render(page, page_count):

        # Header
        ui.clear()
        ui.display.text(10, 30, 'Write down your seed', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)

        render_scrollbar(page, page_count)

        # Mnemonic page
        for pi, (wi, word) in enumerate(mnemonic_pages[page]):
            top = pi * 30 + 74
            pos = wi + 1
            ui.display.text_right(40, top, '%d.' % pos, ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
            ui.display.text(45, top, '%s' % word, ui.BOLD, ui.WHITE, ui.BLACK)

        if page + 1 == page_count:
            # Finish button
            finish = Button((0, 240 - 48, 240, 48), 'Finish',
                            normal_style=CONFIRM_BUTTON,
                            active_style=CONFIRM_BUTTON_ACTIVE)
            yield from finish.wait()
        else:
            # Swipe icon
            yield from animate_swipe()

    yield from paginate(render, len(mnemonic_pages))


@unimport_gen
def layout_reset_device(m):

    # TODO: Failure if not empty

    mnemonic = yield from generate_mnemonic(m.strength, m.display_random)

    # if m.pin_protection:
    #     pin = yield from request_new_pin()
    # else:
    #     pin = None

    yield from show_mnemonic(mnemonic)
