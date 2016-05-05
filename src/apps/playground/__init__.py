from trezor import loop
from trezor import ui
from trezor.utils import unimport_func


def multiplex_touch_events(gens):
    while True:
        e, (x, y) = yield loop.Wait([
            loop.TOUCH_START,
            loop.TOUCH_MOVE,
            loop.TOUCH_END,
        ])
        for gen in gens:
            gen.send((e, (x, y)))


def in_area(pos, area):
    x, y = pos
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


def click_in(area, enter, leave):
    while True:
        e, pos = yield
        if e is not loop.TOUCH_START or not in_area(pos, area):
            continue

        inside = True
        enter()

        while True:
            e, pos = yield
            if e is loop.TOUCH_MOVE:
                if in_area(pos, area):
                    if not inside:
                        enter()
                        inside = True
                else:
                    if inside:
                        leave()
                        inside = False
            elif e is loop.TOUCH_END:
                if in_area(pos, area):
                    return
                else:
                    break


def layout_tap_to_confirm(address, amount, currency):

    ui.display.bar(0, 0, 240, 40, ui.GREEN)
    ui.display.bar(0, 40, 240, 200, ui.WHITE)

    ui.display.text(10, 28, 'Sending', ui.BOLD, ui.WHITE, ui.GREEN)
    ui.display.text(10, 80, '%f %s' % (amount, currency), ui.BOLD, ui.BLACK, ui.WHITE)
    ui.display.text(10, 110, 'to this address:', ui.NORMAL, ui.BLACK, ui.WHITE)
    ui.display.text(10, 140, address[:18], ui.MONO, ui.BLACK, ui.WHITE)
    ui.display.text(10, 160, address[18:], ui.MONO, ui.BLACK, ui.WHITE)

    f = open('apps/playground/tap_64.toig', 'rb')
    bg = ui.WHITE
    style = ui.NORMAL

    def enter():
        nonlocal style
        style = ui.BOLD

    def leave():
        nonlocal style
        style = ui.NORMAL

    def func(fg):
        ui.display.text(68, 212, 'TAP TO CONFIRM', style, fg, bg)
        f.seek(0)
        ui.display.icon(3, 170, f.read(), bg, fg)

    animation = ui.animate_pulse(func, ui.BLACK, ui.GREY, speed=200000)
    click_up = click_in((0, 0, 240, 40), enter, leave)
    click_down = click_in((0, 200, 240, 40), enter, leave)

    next(click_down)
    next(click_up)

    yield loop.Wait((
        animation,
        multiplex_touch_events((
            click_down,
            click_up,
        )),
    ))


@unimport_func
def zprava():
    from _io import BytesIO

    from trezor.messages.GetAddress import GetAddress

    m = GetAddress()
    m.address_n = [1, 2, 3]
    m.show_display = True

    print(m.__dict__)
    f = BytesIO()
    m.dump(f)
    data = f.getvalue()
    f.close()
    print(data)
    # m2 = GetAddress.load(BytesIO(data))
    # print(m2.__dict__)


def dispatch():
    # Callback for HID messages
    print("Dispatch playground")


def boot():
    # Initilize app on boot time.
    # This should hookup HID message types dispatcher() wants to receive.
    print("Boot playground")

    zprava()
