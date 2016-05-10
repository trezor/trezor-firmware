from trezor import loop
from trezor import ui
from trezor.utils import unimport_func


def multiplex_touch_events(gens):
    while True:
        event = yield loop.Wait([
            loop.TOUCH_START,
            loop.TOUCH_MOVE,
            loop.TOUCH_END,
        ])
        for gen in gens:
            gen.send(event)


def in_area(pos, area):
    x, y = pos
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


def click_in(area, click=None, enter=None, leave=None):
    while True:
        e, pos = yield
        if e is not loop.TOUCH_START or not in_area(pos, area):
            continue

        inside = True
        if enter:
            enter()

        while True:
            e, pos = yield
            if e is loop.TOUCH_MOVE:
                if in_area(pos, area):
                    if not inside:
                        if enter:
                            enter()
                        inside = True
                else:
                    if inside:
                        if leave:
                            leave()
                        inside = False
            elif e is loop.TOUCH_END:
                if in_area(pos, area):
                    if click:
                        click()
                    else:
                        return
                else:
                    break


default_button = {
    'bg-color': ui.WHITE,
    'fg-color': ui.BLACK,
    'text-style': ui.NORMAL,
}
default_button_active = {
    'bg-color': ui.GREY,
    'fg-color': ui.BLACK,
    'text-style': ui.BOLD,
}
cancel_button = {
    'bg-color': ui.blend(ui.BLACK, ui.RED, 0.3),
    'fg-color': ui.RED,
    'text-style': ui.NORMAL,
}
cancel_button_active = {
    'bg-color': ui.RED,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
}
confirm_button = {
    'bg-color': ui.blend(ui.BLACK, ui.GREEN, 0.3),
    'fg-color': ui.GREEN,
    'text-style': ui.NORMAL,
}
confirm_button_active = {
    'bg-color': ui.GREEN,
    'fg-color': ui.WHITE,
    'text-style': ui.BOLD,
}


def render_button(area, text, style):
    ax, ay, aw, ah = area
    tx = ax + aw // 2
    ty = ay + ah - 5
    ui.display.bar(ax, ay, aw, ah, style['bg-color'])
    ui.display.text_center(tx, ty, text,
                           style['text-style'],
                           style['fg-color'],
                           style['bg-color'])


def button_widget(area, text,
                  click=None,
                  style=default_button,
                  active_style=default_button_active):

    def enter():
        render_button(area, text, active_style)

    def leave():
        render_button(area, text, style)

    def _click():
        leave()
        click()

    render_button(area, text, style)
    return click_in(area, _click, enter, leave)


def pin_widget():

    pin = ''
    width = const(80)
    height = const(60)
    margin = const(5)

    def digit_area(d):
        x = ((d - 1) % 3) * width
        y = ((d - 1) // 3) * height
        return (
            x + margin,
            y + margin,
            width - margin,
            height - margin
        )

    def append_digit(d):
        pin += str(d)
        print('PIN so far: ', pin)

    def digit_widget(digit):
        nonlocal pin
        area = digit_area(digit)
        button = button_widget(
            area,
            str(digit),
            lambda: append_digit(digit))
        return button

    digits = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    buttons = [digit_widget(d) for d in digits]

    def cancel():
        raise StopIteration(None)

    def confirm():
        raise StopIteration(pin)

    cancel_widget = button_widget((0, 240 - 60, 120, 60), 'Cancel',
                                  click=cancel,
                                  style=cancel_button,
                                  active_style=cancel_button_active)
    confirm_widget = button_widget((120, 240 - 60, 120, 60), 'Confirm',
                                   click=confirm,
                                   style=confirm_button,
                                   active_style=confirm_button_active)

    buttons.append(cancel_widget)
    buttons.append(confirm_widget)
    for but in buttons:
        next(but)

    return buttons


def layout_tap_to_confirm(address, amount, currency):

    # ui.display.bar(0, 0, 240, 40, ui.GREEN)
    # ui.display.bar(0, 40, 240, 200, ui.WHITE)

    # ui.display.text(10, 28, 'Sending', ui.BOLD, ui.WHITE, ui.GREEN)
    # ui.display.text(10, 80, '%f %s' % (amount, currency), ui.BOLD, ui.BLACK, ui.WHITE)
    # ui.display.text(10, 110, 'to this address:', ui.NORMAL, ui.BLACK, ui.WHITE)
    # ui.display.text(10, 140, address[:18], ui.MONO, ui.BLACK, ui.WHITE)
    # ui.display.text(10, 160, address[18:], ui.MONO, ui.BLACK, ui.WHITE)

    # f = open('apps/playground/tap_64.toig', 'rb')
    # bg = ui.WHITE
    # style = ui.NORMAL

    # def func(fg):
    #     ui.display.text(68, 212, 'TAP TO CONFIRM', style, fg, bg)
    #     f.seek(0)
    #     ui.display.icon(3, 170, f.read(), bg, fg)

    # animation = ui.animate_pulse(func, ui.BLACK, ui.GREY, speed=200000)

    # button = button_widget((20, 20, 210, 60), 'HELLO WORLD!')
    # next(button)

    pin = pin_widget()

    result = yield loop.Wait((
        # animation,
        multiplex_touch_events(pin),
    ))

    print(result)


@unimport_func
def zprava():
    from uio import BytesIO

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
