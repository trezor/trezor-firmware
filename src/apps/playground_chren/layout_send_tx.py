from trezor import ui
from trezor import loop
from trezor import res
from trezor.ui.scroll import Scroll

def layout_send_tx():

	# paint background black
    ui.display.bar(0, 0, 240, 240, ui.BLACK)

    # top header bar
    # ui.display.bar(0, 0, 240, 48, ui.PM_BLUE, ui.BLACK, 4)
    ui.display.icon(10, 9, res.load('apps/playground_chren/res/arrow-up2.toig'), ui.BLACK, ui.PM_BLUE)
    ui.display.text(40, 28, 'Sending coins', ui.BOLD, ui.PM_BLUE, ui.BLACK)


    # content 
    ui.display.bar(0, 42, 240, 198, ui.BLACK)
    ui.display.text(10, 70, 'Amount:', ui.BOLD, ui.GREY, ui.BLACK)
    ui.display.text(10, 100, '0.0000341 BTC', ui.MONO, ui.WHITE, ui.BLACK)
    ui.display.text(10, 130, 'To address:', ui.BOLD, ui.GREY, ui.BLACK)
    ui.display.text(10, 160, '1NDpZ2wyFekVezssS', ui.MONO, ui.WHITE, ui.BLACK)
    ui.display.text(10, 185, 'Xv2tmQgmxcoHMUJ7u', ui.MONO, ui.WHITE, ui.BLACK)

    scroll = Scroll(page=0, totale_lines=20, lines_per_page=4)
    scroll.render()


   	# swipe down indicator
    def func_top(foreground):
        ui.display.bar(102, 214, 36, 4, foreground, ui.BLACK, 2)

    def func_middle(foreground):
        ui.display.bar(106, 222, 28, 4, foreground, ui.BLACK, 2)

    def func_bottom(foreground):
        ui.display.bar(110, 230, 20, 4, foreground, ui.BLACK, 2)

    animation_top = ui.animate_pulse(func_top, ui.PM_BLUE, ui.PM_DARK_BLUE, speed=300000, delay=0)
    animation_middle = ui.animate_pulse(func_middle, ui.PM_BLUE, ui.PM_DARK_BLUE, speed=300000, delay=200000)
    animation_bottom = ui.animate_pulse(func_bottom, ui.PM_BLUE, ui.PM_DARK_BLUE, speed=300000, delay=400000)

    yield loop.Wait([animation_top, animation_middle, animation_bottom])