from trezor import ui, wire
from trezor.utils import unimport


def nth(n):
    if 4 <= n % 100 <= 20:
        sfx = 'th'
    else:
        sfx = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + sfx


@unimport
async def layout_recovery_device(ctx, msg):

    msg = 'Please enter ' + nth(msg.word_count) + ' word'

    ui.display.clear()
    ui.header('Recovery device', ui.ICON_RECOVERY, ui.BLACK, ui.LIGHT_GREEN)
    ui.display.text(10, 74, msg, ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text(10, 104, 'of your mnemonic.', ui.BOLD, ui.WHITE, ui.BLACK)

    # TODO
