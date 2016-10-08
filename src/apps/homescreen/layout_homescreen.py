from trezor import ui, loop, res
from trezor.utils import unimport

async def swipe_to_rotate():
    from trezor.ui.swipe import Swipe

    while True:
        degrees = await Swipe(absolute=True)
        ui.display.orientation(degrees)


'''
async def animate_logo():
    image = res.load('apps/homescreen/res/trezor.toig')

    def render(fg):
        ui.display.icon(0, 0, image, fg, ui.BLACK)
    await ui.animate_pulse(render, ui.WHITE, ui.DARK_GREY, speed=800000)
'''

async def dim_screen():
    current = ui.display.backlight()

    await loop.Sleep(5*1000000)
    await ui.backlight_slide(ui.BACKLIGHT_DIM)

    try:
        while True:
            await loop.Sleep(1000000)
    except:
        # Return back to original brightness
        ui.display.backlight(current)

@unimport
async def layout_homescreen():
    image = res.load('apps/homescreen/res/trezor.toig')
    ui.display.icon(0, 0, image, ui.WHITE, ui.BLACK)

    ui.display.backlight(ui.BACKLIGHT_NORMAL)
    await loop.Wait([swipe_to_rotate(), dim_screen()])