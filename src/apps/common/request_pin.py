from trezor import ui
from trezor import wire
from trezor.utils import unimport


@unimport
async def request_pin(session_id, *args, **kwargs):
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import ProtectCall
    from trezor.messages.FailureType import PinCancelled
    from trezor.messages.wire_types import ButtonAck
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.ui.pin import PinMatrix

    await wire.reply_message(session_id,
                             ButtonRequest(code=ProtectCall),
                             ButtonAck)

    ui.display.clear()
    matrix = PinMatrix(*args, **kwargs)
    dialog = ConfirmDialog(matrix)
    if await dialog != CONFIRMED:
        raise wire.FailureError(PinCancelled, 'PIN cancelled')

    return matrix.pin


@unimport
async def request_pin_twice(session_id):
    from trezor.messages.FailureType import PinInvalid

    pin_first = await request_pin(session_id)
    pin_again = await request_pin(session_id, 'Enter PIN again')
    if pin_first != pin_again:
        raise wire.FailureError(PinInvalid, 'PIN invalid')

    return pin_first
