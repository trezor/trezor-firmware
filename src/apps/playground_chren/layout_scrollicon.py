from trezor import ui
from trezor import loop

def layout_scrollicon():

    def func_top(foreground):
        ui.display.bar(102, 216, 36, 4, foreground)

    def func_middle(foreground):
        ui.display.bar(106, 223, 28, 4, foreground)

    def func_bottom(foreground):
        ui.display.bar(110, 230, 20, 4, foreground)

    animation_top = ui.animate_pulse(func_top, ui.GREY, ui.BLACK, speed=300000, delay=0)
    animation_middle = ui.animate_pulse(func_middle, ui.GREY, ui.BLACK, speed=300000, delay=100000)
    animation_bottom = ui.animate_pulse(func_bottom, ui.GREY, ui.BLACK, speed=300000, delay=200000)

    yield loop.Wait([animation_top, animation_middle, animation_bottom])
