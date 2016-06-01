from trezor import wire
from trezor import ui
from trezor.utils import unimport_gen


@unimport_gen
def confirm():
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import Other
    from trezor.messages.ButtonAck import ButtonAck

    dialog = ConfirmDialog()
    dialog.render()

    ack = yield from wire.call(ButtonRequest(code=Other), ButtonAck)
    res = yield from dialog.wait()

    return res == CONFIRMED


@unimport_gen
def layout_load_device(message):

    ui.clear()
    ui.display.text_center(120, 40, 'Really load device?', ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text_center(120, 100, 'Never do this, please.', ui.NORMAL, ui.WHITE, ui.BLACK)

    confirmed = yield from confirm()

    if confirmed:
        from trezor.messages.Success import Success
        wire.write(Success(message='Loaded'))
    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        wire.write(Failure(message='Cancelled', code=ActionCancelled))
