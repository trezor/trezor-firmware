from trezor import loop
from trezor import ui
from trezor.utils import unimport_func

def layout_tap_to_confirm(address, amount, currency):

    ui.display.bar(0, 0, 240, 40, ui.GREEN)
    ui.display.bar(0, 40, 240, 200, ui.WHITE)

    ui.display.text(10, 28, 'Sending', ui.BOLD, ui.WHITE, ui.GREEN)
    ui.display.text(10, 80, '%f %s' % (amount, currency), ui.BOLD, ui.BLACK, ui.WHITE)
    ui.display.text(10, 110, 'to this address:', ui.NORMAL, ui.BLACK, ui.WHITE)
    ui.display.text(10, 140, address[:18], ui.MONO, ui.BLACK, ui.WHITE)
    ui.display.text(10, 160, address[18:], ui.MONO, ui.BLACK, ui.WHITE)

    f = open('apps/playground/tap_64.toig', 'rb')
    _background = ui.WHITE

    def func(foreground):
        ui.display.text(68, 212, 'TAP TO CONFIRM', ui.BOLD, foreground, _background)

        f.seek(0)
        ui.display.icon(3, 170, f.read(), _background, foreground)

    yield from ui.animate_pulse(func, ui.BLACK, ui.GREY, speed=200000)

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
