from trezor import ui, loop, res
from trezor.utils import unimport


async def swipe_to_rotate():
    from trezor.ui.swipe import Swipe, degrees

    swipe = await Swipe(absolute=True)
    ui.display.orientation(degrees(swipe))


async def dim_screen():
    await loop.sleep(5 * 1000000)
    await ui.backlight_slide(ui.BACKLIGHT_DIM)
    while True:
        await loop.sleep(10000000)


@ui.layout
async def display_homescreen():
    from apps.common import storage

    if not storage.is_initialized():
        label = 'Open trezor.io/start'
        image = None
    else:
        label = storage.get_label() or 'My TREZOR'
        image = storage.get_homescreen()

    if not image:
        image = res.load('apps/homescreen/res/homescreen.toif')

    ui.display.bar(0, 0, ui.SCREEN, ui.SCREEN, ui.BG)
    ui.display.avatar((ui.SCREEN - 144) // 2, (ui.SCREEN - 144) // 2 - 10, image, ui.WHITE, ui.BLACK)
    ui.display.text_center(ui.SCREEN // 2, ui.SCREEN - 20, label, ui.BOLD, ui.FG, ui.BG)

    await dim_screen()


@unimport
async def layout_homescreen():
    while True:
        await loop.wait(swipe_to_rotate(), display_homescreen())
