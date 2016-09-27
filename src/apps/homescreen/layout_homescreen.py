from trezor import ui, loop, res
from trezor.utils import unimport


async def swipe_to_rotate():
    from trezor.ui.swipe import Swipe

    while True:
        degrees = await Swipe(absolute=True)
        ui.display.orientation(degrees)


async def animate_logo():
    image = res.load('apps/homescreen/res/experiment1.toif')
    ui.display.image(0, 0, image)


@unimport
async def layout_homescreen():
    await loop.Wait([swipe_to_rotate(), animate_logo()])
