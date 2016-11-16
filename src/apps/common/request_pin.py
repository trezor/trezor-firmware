from trezor import ui
from trezor import wire
from trezor.utils import unimport

# TODO: publish only when debuglink is on
matrix = None


@unimport
async def request_pin_on_display(session_id: int, code: int=None) -> str:
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import ProtectCall
    from trezor.messages.FailureType import PinCancelled
    from trezor.messages.wire_types import ButtonAck
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.ui.pin import PinMatrix

    global matrix

    _, label = _get_code_and_label(code)

    await wire.reply_message(session_id,
                             ButtonRequest(code=ProtectCall),
                             ButtonAck)

    ui.display.clear()
    matrix = PinMatrix(label)
    dialog = ConfirmDialog(matrix)
    pin = matrix.pin
    matrix = None

    if await dialog != CONFIRMED:
        raise wire.FailureError(PinCancelled, 'PIN cancelled')
    return pin


@unimport
async def request_pin_on_client(session_id: int, code: int=None) -> str:
    from trezor.messages.FailureType import PinCancelled
    from trezor.messages.PinMatrixRequest import PinMatrixRequest
    from trezor.messages.wire_types import PinMatrixAck, Cancel
    from trezor.ui.pin import PinMatrix

    global matrix

    code, label = _get_code_and_label(code)

    ui.display.clear()
    matrix = PinMatrix(label)
    matrix.render()

    ack = await wire.reply_message(session_id,
                                   PinMatrixRequest(code=code),
                                   PinMatrixAck, Cancel)
    digits = matrix.digits
    matrix = None

    if ack.WIRE_TYPE == Cancel:
        raise wire.FailureError(PinCancelled, 'PIN cancelled')
    return _decode_pin(ack.pin, digits)


request_pin = request_pin_on_client


@unimport
async def request_pin_twice(session_id: int) -> str:
    from trezor.messages.FailureType import PinInvalid
    from trezor.messages import PinMatrixRequestType

    pin_first = await request_pin(session_id, PinMatrixRequestType.NewFirst)
    pin_again = await request_pin(session_id, PinMatrixRequestType.NewSecond)
    if pin_first != pin_again:
        raise wire.FailureError(PinInvalid, 'PIN invalid')

    return pin_first


def _get_code_and_label(code: int) -> str:
    from trezor.messages import PinMatrixRequestType
    if code is None:
        code = PinMatrixRequestType.Current
    if code == PinMatrixRequestType.NewFirst:
        label = 'Enter new PIN'
    elif code == PinMatrixRequestType.NewSecond:
        label = 'Enter new PIN again'
    else:  # PinMatrixRequestType.Current
        label = 'Enter PIN'
    return code, label


def _decode_pin(pin: str, secret: list) -> str:
    return ''.join([str(secret[int(d) - 1]) for d in pin])
