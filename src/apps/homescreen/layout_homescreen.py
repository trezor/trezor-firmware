from trezor import ui, loop, res
from trezor.ui.swipe import Swipe


async def swipe_to_rotate():
    while True:
        degrees = await Swipe(absolute=True)
        ui.display.orientation(degrees)


async def animate_logo():
    icon = res.load('apps/homescreen/res/trezor.toig')
    async for fg in ui.pulse_animation(ui.WHITE, ui.GREY, speed=400000):
        ui.display.icon(0, 0, icon, fg, ui.BLACK)


async def layout_homescreen():
    await loop.Wait([swipe_to_rotate(), animate_logo()])
