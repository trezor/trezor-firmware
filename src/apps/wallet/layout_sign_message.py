from trezor import wire, ui
from trezor.utils import unimport
from trezor.workflows.confirm import confirm


@unimport
def layout_sign_message(message):
    ui.clear()
    ui.display.text(10, 30, 'Signing message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, message.message, ui.MONO, ui.WHITE, ui.BLACK)
    confirmed = yield from confirm(confirm='Sign')

    if confirmed:
        from trezor.messages.Success import Success
        yield from wire.write(Success(message='Signed'))
    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        yield from wire.write(Failure(message='Cancelled', code=ActionCancelled))
