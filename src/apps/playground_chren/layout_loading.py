from trezor import ui
from trezor import loop
from trezor import res

def layout_loading():
    
    ui.display.text_center(120, 240 - 18, 'Processing ...', ui.BOLD, ui.WHITE, ui.BLACK)
    p = 0

    def func(foreground):
        ui.display.loader(p, ui.YELLOW, 0, res.load('apps/playground_chren/res/gears3.toig'), ui.WHITE)
        p = (p + 10) % 1000

    animation = ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)

    yield from animation
