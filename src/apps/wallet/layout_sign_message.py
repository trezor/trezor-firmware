from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_sign_message(message, session_id):
    from trezor.messages.Success import Success

    ui.display.clear()
    ui.display.text(10, 30, 'Signing message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, message.message, ui.MONO, ui.WHITE, ui.BLACK)

    # TODO

    return Success(message='Signed')
