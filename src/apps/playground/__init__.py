from trezor import loop
from trezor import ui
from trezor.utils import unimport_func


def in_area(pos, area):
    x, y = pos
    ax, ay, aw, ah = area
    return ax <= x <= ax + aw and ay <= y <= ay + ah


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


BTN_CLICKED = const(1)

BTN_STARTED = const(1)
BTN_ACTIVE = const(2)
BTN_DIRTY = const(4)


class Button():

    def __init__(self, area, text,
                 style=default_button,
                 active_style=default_button_active):
        self.area = area
        self.text = text
        self.style = style
        self.active_style = active_style
        self.state = BTN_DIRTY

    def render(self):
        if not self.state & BTN_DIRTY:
            return
        state = self.state & ~BTN_DIRTY
        style = self.active_style if state & BTN_ACTIVE else self.style
        ax, ay, aw, ah = self.area
        tx = ax + aw // 2
        ty = ay + ah - 5
        ui.display.bar(ax, ay, aw, ah, style['bg-color'])
        ui.display.text_center(tx, ty, self.text,
                               style['text-style'],
                               style['fg-color'],
                               style['bg-color'])
        self.state = state

    def progress(self, event, pos):
        if event is loop.TOUCH_START:
            if in_area(pos, self.area):
                self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
        elif event is loop.TOUCH_MOVE and self.state & BTN_STARTED:
            if in_area(pos, self.area):
                if not self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY | BTN_ACTIVE
            else:
                if self.state & BTN_ACTIVE:
                    self.state = BTN_STARTED | BTN_DIRTY
        elif event is loop.TOUCH_END and self.state & BTN_STARTED:
            self.state = BTN_DIRTY
            if in_area(pos, self.area):
                return BTN_CLICKED


def digit_area(d):
    width = const(80)
    height = const(60)
    margin = const(1)
    x = ((d - 1) % 3) * width
    y = ((d - 1) // 3) * height
    return (
        x + margin,
        y + margin,
        width - margin,
        height - margin)


PIN_CONFIRMED = const(1)
PIN_CANCELLED = const(2)


class PinDialog():

    def __init__(self):
        self.confirm_button = Button(
            (0, 240-60, 120, 60), 'Confirm',
            style=confirm_button,
            active_style=confirm_button_active)
        self.cancel_button = Button(
            (120, 240-60, 120, 60), 'Cancel',
            style=cancel_button,
            active_style=cancel_button_active)
        self.pin_buttons = [
            Button(digit_area(d), str(d)) for d in range(1, 10)]
        self.pin = ''

    def render(self):
        for b in self.pin_buttons:
            b.render()
        self.confirm_button.render()
        self.cancel_button.render()

    def progress(self, event, pos):
        for b in self.pin_buttons:
            if b.progress(event, pos) is BTN_CLICKED:
                self.pin += b.text
        if self.confirm_button.progress(event, pos) is BTN_CLICKED:
            return PIN_CONFIRMED
        if self.cancel_button.progress(event, pos) is BTN_CLICKED:
            return PIN_CANCELLED


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

    pin = PinDialog()

    while True:
        pin.render()

        # TODO: if we simply wait for any of scalar events, we can use
        # something much more lightweight than loop.Wait
        event, pos = yield loop.Wait([
            loop.TOUCH_START,
            loop.TOUCH_MOVE,
            loop.TOUCH_END,
        ])
        result = pin.progress(event, pos)
        if result is PIN_CONFIRMED:
            print('PIN confirmed:', pin.pin)
            return
        elif result is PIN_CANCELLED:
            print('PIN CANCELLED, go home')
            return


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
