from trezor import ui, wire
from trezor.utils import unimport_gen


def nth(n):
    if 4 <= n % 100 <= 20:
        sfx = 'th'
    else:
        sfx = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + sfx


@unimport_gen
def layout_recovery_device(message):

    msg = 'Please enter ' + nth(message.word_count) + ' word'

    ui.clear()
    ui.display.text(10, 30, 'Recovering device', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 74, msg, ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text(10, 104, 'of your mnemonic.', ui.BOLD, ui.WHITE, ui.BLACK)
    yield from wire.read(None)
