from trezor import ui, loop, res
from trezor.utils import unimport


async def swipe_to_rotate():
    from trezor.ui.swipe import Swipe

    degrees = await Swipe(absolute=True)
    ui.display.orientation(degrees)


async def dim_screen():
    await loop.Sleep(5 * 1000000)
    await ui.backlight_slide(ui.BACKLIGHT_DIM)
    while True:
        await loop.Sleep(1000000)


def display_homescreen():
    from apps.common import storage

    image = res.load('apps/homescreen/res/trezor_logo.toig')
    ui.display.icon(0, 0, image, ui.WHITE, ui.BLACK)

    if not storage.is_initialized():
        label = 'Go to trezor.io/start'
    else:
        label = storage.get_label()
        if not label:
            label = 'My TREZOR'
    ui.display.text_center(120, 210, label, ui.BOLD, ui.WHITE, ui.BLACK)


@unimport
async def layout_homescreen():
    while True:
        display_homescreen()
        await loop.Wait([swipe_to_rotate(), dim_screen()])
