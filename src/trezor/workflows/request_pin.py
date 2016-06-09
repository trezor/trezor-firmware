from trezor import ui
from trezor import wire
from trezor import config
from trezor.utils import unimport_gen

MGMT_APP = const(1)

PASSPHRASE_PROTECT = (1)  # 0 | 1
PIN_PROTECT = const(2)  # 0 | 1
PIN = const(4)  # str


def prompt_pin(*args, **kwargs):
    from trezor.ui.pin import PinMatrix
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED

    ui.clear()

    matrix = PinMatrix(*args, **kwargs)
    dialog = ConfirmDialog(matrix)
    result = yield from dialog.wait()

    return matrix.pin if result == CONFIRMED else None


def request_pin(*args, **kwargs):
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import ProtectCall
    from trezor.messages.ButtonAck import ButtonAck

    ack = yield from wire.call(ButtonRequest(code=ProtectCall), ButtonAck)
    pin = yield from prompt_pin(*args, **kwargs)

    return pin


def change_pin():
    pass


@unimport_gen
def protect_with_pin():
    from trezor.messages.Failure import Failure
    from trezor.messages.FailureType import PinInvalid
    from trezor.messages.FailureType import ActionCancelled

    pin_protect = config.get(MGMT_APP, PIN_PROTECT)
    if not pin_protect:
        return

    entered_pin = yield from request_pin()
    if entered_pin is None:
        yield from wire.write(Failure(code=ActionCancelled, message='Cancelled'))
        raise Exception('Cancelled')

    stored_pin = config.get(MGMT_APP, PIN)
    if stored_pin != entered_pin:
        yield from wire.write(Failure(code=PinInvalid, message='PIN invalid'))
        raise Exception('PIN invalid')
