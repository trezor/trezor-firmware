from trezor import ui
from trezor import loop

def layout_scrollicon():

    def func_top(foreground):
        ui.display.bar(102, 214, 36, 4, foreground, ui.BLACK, 2)

    def func_middle(foreground):
        ui.display.bar(106, 222, 28, 4, foreground, ui.BLACK, 2)

    def func_bottom(foreground):
        ui.display.bar(110, 230, 20, 4, foreground, ui.BLACK, 2)

    animation_top = ui.animate_pulse(func_top, ui.DARK_GREY, ui.LIGHT_GREY, speed=300000, delay=0)
    animation_middle = ui.animate_pulse(func_middle, ui.DARK_GREY, ui.LIGHT_GREY, speed=300000, delay=100000)
    animation_bottom = ui.animate_pulse(func_bottom, ui.DARK_GREY, ui.LIGHT_GREY, speed=300000, delay=200000)

    yield loop.Wait([animation_top, animation_middle, animation_bottom])
