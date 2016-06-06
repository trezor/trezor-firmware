from trezor import wire
from trezor import ui
from trezor.utils import unimport_gen
from trezor.workflows.confirm import confirm


@unimport_gen
def layout_wipe_device(message):

    ui.clear()
    ui.display.text_center(120, 40, 'Really wipe device?', ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text_center(120, 100, 'You might regret it!', ui.NORMAL, ui.WHITE, ui.BLACK)

    confirmed = yield from confirm()

    if confirmed:
        from trezor.messages.Success import Success
        yield from wire.write(Success(message='Wiped'))
    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        yield from wire.write(Failure(message='Cancelled', code=ActionCancelled))
