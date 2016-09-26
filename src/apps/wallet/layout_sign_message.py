from trezor import wire, ui
from trezor.utils import unimport


@unimport
async def layout_sign_message(message):
    from trezor.workflows.confirm import protect_with_confirm
    from trezor.messages.Success import Success

    ui.clear()
    ui.display.text(10, 30, 'Signing message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 60, message.message, ui.MONO, ui.WHITE, ui.BLACK)

    await protect_with_confirm(confirm='Sign')

    # TODO

    return Success(message='Signed')
