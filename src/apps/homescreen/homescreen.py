from trezor import ui, loop, res
from trezor.utils import unimport


async def swipe_to_rotate():
    from trezor.ui.swipe import Swipe

    while True:
        degrees = await Swipe(absolute=True)
        ui.display.orientation(degrees)


async def dim_screen():
    current = ui.display.backlight()

    await loop.Sleep(5 * 1000000)
    await ui.backlight_slide(ui.BACKLIGHT_DIM)

    try:
        while True:
            await loop.Sleep(1000000)
    finally:
        # Return back to original brightness
        ui.display.backlight(current)


def display_homescreen():
    from apps.common import storage

    image = res.load('apps/homescreen/res/trezor.toig')
    ui.display.icon(0, 0, image, ui.WHITE, ui.BLACK)

    ui.display.bar(0, 180, 240, 240, ui.BLACK)

    label = storage.get_label() or 'My TREZOR'
    ui.display.text_center(120, 210, label, ui.BOLD, ui.WHITE, ui.BLACK)


@unimport
async def layout_homescreen():
    display_homescreen()
    ui.display.backlight(ui.BACKLIGHT_NORMAL)
    await loop.Wait([swipe_to_rotate(), dim_screen()])
