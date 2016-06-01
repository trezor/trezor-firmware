from trezor import loop
from trezor import ui
from trezor import msg
from trezor.ui.pin import PinDialog, PIN_CONFIRMED, PIN_CANCELLED
from trezor.utils import unimport_gen
from trezor.res import loadres


@unimport_gen
def layout_tap_to_confirm(address, amount, currency):

    # ui.display.bar(0, 0, 240, 40, ui.GREEN)
    # ui.display.bar(0, 40, 240, 200, ui.WHITE)

    # ui.display.text(10, 28, 'Sending', ui.BOLD, ui.WHITE, ui.GREEN)
    # ui.display.text(10, 80, '%f %s' % (amount, currency), ui.BOLD, ui.BLACK, ui.WHITE)
    # ui.display.text(10, 110, 'to this address:', ui.NORMAL, ui.BLACK, ui.WHITE)
    # ui.display.text(10, 140, address[:18], ui.MONO, ui.BLACK, ui.WHITE)
    # ui.display.text(10, 160, address[18:], ui.MONO, ui.BLACK, ui.WHITE)

    # bg = ui.WHITE
    # style = ui.NORMAL

    # def func(fg):
    #     ui.display.text(68, 212, 'TAP TO CONFIRM', style, fg, bg)
    #     ui.display.icon(3, 170, loadres('apps/playground/res/tap_64.toig'), bg, fg)

    # animation = ui.animate_pulse(func, ui.BLACK, ui.GREY, speed=200000)

    # pin_dialog = PinDialog()
    # pin_result = yield from pin_dialog.wait_for_result()

    # if pin_result is PIN_CONFIRMED:
    #     print('PIN confirmed:', pin_dialog.pin)

    # elif pin_result is PIN_CANCELLED:
    #     print('PIN CANCELLED, go home')

    from trezor.messages.Initialize import Initialize
    from trezor.messages.Features import Features
    from trezor.messages.GetPublicKey import GetPublicKey
    from trezor.messages.PinMatrixRequest import PinMatrixRequest
    from trezor.messages.PinMatrixRequestType import Current
    from trezor.messages.PinMatrixAck import PinMatrixAck
    from trezor.messages.PublicKey import PublicKey
    from trezor.messages.HDNodeType import HDNodeType

    m = yield from msg.read_msg(Initialize)
    print('Initialize')

    m = Features()
    m.revision = 'deadbeef'
    m.bootloader_hash = 'deadbeef'
    m.device_id = 'DEADBEEF'
    m.coins = []
    m.imported = False
    m.initialized = True
    m.label = 'My TREZOR'
    m.major_version = 2
    m.minor_version = 0
    m.patch_version = 0
    m.pin_cached = False
    m.pin_protection = True
    m.passphrase_cached = False
    m.passphrase_protection = False
    m.vendor = 'bitcointrezor.com'

    m = yield from msg.call(m, GetPublicKey)
    print('GetPublicKey', m.address_n)

    m = PinMatrixRequest()
    m.type = Current

    m = yield from msg.call(m, PinMatrixAck)
    print('PinMatrixAck', m.pin)

    m = PublicKey()
    m.node = HDNodeType()
    m.node.depth = 0
    m.node.child_num = 0
    m.node.fingerprint = 0
    m.node.chain_code = 'deadbeef'
    m.node.public_key = 'deadbeef'

    m = yield from msg.call(m, Initialize)
    print('Initialize')


def dispatch():
    # Callback for HID messages
    print("Dispatch playground")


def boot():
    # Initilize app on boot time.
    # This should hookup HID message types dispatcher() wants to receive.
    print("Boot playground")
