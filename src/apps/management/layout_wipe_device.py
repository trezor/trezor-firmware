from trezor import wire
from trezor import ui
from trezor.utils import unimport
from trezor.workflows.confirm import confirm


@unimport
def layout_wipe_device(message):

    ui.clear()
    ui.display.text(10, 30, 'Wiping device', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 74, 'Do you really want to',
                    ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text(10, 104, 'wipe the device?', ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text(10, 164, 'All data will be lost.',
                    ui.NORMAL, ui.WHITE, ui.BLACK)

    confirmed = yield from confirm()

    if confirmed:
        from trezor.messages.Success import Success
        yield from wire.write(Success(message='Wiped'))
    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        yield from wire.write(Failure(message='Cancelled', code=ActionCancelled))
