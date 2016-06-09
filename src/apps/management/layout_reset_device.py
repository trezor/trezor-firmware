from trezor import wire, loop, res, ui
from trezor.ui.swipe import Swipe, SWIPE_UP, SWIPE_DOWN
from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from trezor.crypto import hashlib, random, bip39
from trezor.utils import unimport_gen


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
    from trezor.workflows.pin import request_pin

    pin = yield from request_pin()
    pin_again = yield from request_pin('Enter PIN again')

    if pin == pin_again:
        return pin
    else:
        raise Exception()  # TODO: wrong PIN should be handled in unified way


@unimport_gen
def layout_reset_device(m):

    # TODO: Failure if not empty

    mnemonic = yield from generate_mnemonic(m.strength, m.display_random)

    if m.pin_protection:
        pin = yield from request_new_pin()
    else:
        pin = None

    mnemonic_words = mnemonic.split()
    words_per_page = const(4)

    def render(page):
        ui.clear()
        ui.display.text(10, 30, 'Write down your seed', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
        for i in range(0, words_per_page):
            index = i + page * words_per_page
            word = mnemonic_words[index]
            top = 74 + i * 30
            ui.display.text_right(40, top, '%d.' % (index + 1), ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
            ui.display.text(45, top, '%s' % word, ui.BOLD, ui.WHITE, ui.BLACK)
        if(len(mnemonic_words) // words_per_page == page + 1):
            finish = Button((0, 240 - 48, 240, 48), 'Finish', normal_style=CONFIRM_BUTTON, active_style=CONFIRM_BUTTON_ACTIVE)
            finish.render()

    def paginate():
        count = len(mnemonic_words) // words_per_page
        page = 0
        while True:
            render(page)
            degrees = yield from Swipe().wait()
            if degrees == SWIPE_UP:
                page = min(page + 1, count - 1)
            elif degrees == SWIPE_DOWN:
                page = max(page - 1, 0)

    def animate_arrow():
        def func(foreground):
            ui.display.icon(105, 200, res.load('apps/management/res/small-arrow.toig'), foreground, ui.BLACK)
        yield from ui.animate_pulse(func, ui.WHITE, ui.BLACK, speed=190000)

    yield loop.Wait([paginate(),
                     animate_arrow()])
