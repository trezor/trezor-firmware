from trezor import ui
from trezor import loop


def layout_homescreen():
    print("Homescreen layout!")

    # ui.display.bar(0, 0, 240, 240, ui.WHITE)

    # f = open('apps/homescreen/trezor.toig', 'r')

    # def func(foreground):
    #     f.seek(0)
    #     ui.display.icon(0, 0, f.read(), foreground, ui.BLACK)

    # animation = ui.animate_pulse(func, ui.WHITE, ui.GREY, speed=400000)

    timeout = loop.sleep(1000 * 1000)

    yield loop.wait([timeout])
    print('back to layout')

    # try:
    #     print(animation.throw(StopIteration()))
    # except:
    #     pass

    # from apps import playground
    # return playground.layout_tap_to_confirm('1BitkeyP2nDd5oa64x7AjvBbbwST54W5Zmx2', 110.126967, 'BTC')
