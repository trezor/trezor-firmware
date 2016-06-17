from trezor import wire, loop, res, ui
from trezor.ui.swipe import Swipe, SWIPE_UP, SWIPE_DOWN
from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from trezor.ui.scroll import Scroll
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


def change_page(page, page_count):
    while True:
        swipe = yield from Swipe().wait()
        if swipe == SWIPE_UP and page < page_count - 1:  # Scroll down
            return page + 1
        elif swipe == SWIPE_DOWN and page > 0:  # Scroll up
            return page - 1

def paginate(render_page, page_count, page=0):
    while True:
        changer = change_page(page, page_count)
        renderer = render_page(page, page_count)
        waiter = loop.Wait([changer, renderer])
        result = yield waiter
        if changer in waiter.finished:
            page = result
        else:
            return result


def render_scrollbar(page, page_count):
    screen_height = const(220)
    size = const(8)

    padding = 15
    if page_count * padding > screen_height:
        padding = screen_height // page_count

    x = 225
    y = (screen_height // 2) - (page_count // 2) * padding

    for i in range(0, page_count):
        if i != page:
            ui.display.bar(x, y + i * padding, size, size, ui.GREY, ui.BLACK, 4)
    ui.display.bar(x, y + page * padding, size, size, ui.WHITE, ui.BLACK, 4)


def animate_swipe():
    def render(fg):
        ui.display.bar(102, 214, 36, 4, fg, ui.BLACK, 2)
        ui.display.bar(106, 222, 28, 4, fg, ui.BLACK, 2)
        ui.display.bar(110, 230, 20, 4, fg, ui.BLACK, 2)
    yield from ui.animate_pulse(render, ui.WHITE, ui.GREY, speed=300000, delay=200000)


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

        # Finish button
        if page + 1 == page_count:
            finish = Button((0, 240 - 48, 240, 48), 'Finish',
                            normal_style=CONFIRM_BUTTON,
                            active_style=CONFIRM_BUTTON_ACTIVE)
            yield from finish.wait()

        # Swipe icon
        else:
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
