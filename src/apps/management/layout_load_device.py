from trezor import wire
from trezor import ui
from trezor.utils import unimport
from trezor.workflows.confirm import confirm


@unimport
def layout_load_device(message):

    ui.clear()
    ui.display.text_center(120, 40, 'Really load device?',
                           ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text_center(
        120, 100, 'Never do this, please.', ui.NORMAL, ui.WHITE, ui.BLACK)

    confirmed = yield from confirm()

    if confirmed:
        from trezor.messages.Success import Success
        yield from wire.write(Success(message='Loaded'))
    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        yield from wire.write(Failure(message='Cancelled', code=ActionCancelled))
