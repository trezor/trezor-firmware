from trezor import wire
from trezor.utils import unimport_gen


@unimport_gen
def request_pin():
    from trezor.ui.pin import PinMatrix
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import ProtectCall
    from trezor.messages.ButtonAck import ButtonAck

    matrix = PinMatrix()
    dialog = ConfirmDialog(matrix)
    dialog.render()

    ack = yield from wire.call(ButtonRequest(code=ProtectCall), ButtonAck)
    res = yield from dialog.wait()

    return matrix.pin if res == CONFIRMED else None
