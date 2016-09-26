from trezor import wire
from trezor import ui
from trezor.utils import unimport
from trezor.workflows.confirm import protect_with_confirm

from .storage import clear_storage


@unimport
async def layout_wipe_device(message, session_id):
    from trezor.messages.Success import Success

    ui.clear()
    ui.display.text(10, 30, 'Wiping device', ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
    ui.display.text(10, 74, 'Do you really want to',
                    ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text(10, 104, 'wipe the device?', ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text(10, 164, 'All data will be lost.',
                    ui.NORMAL, ui.WHITE, ui.BLACK)

    await protect_with_confirm(session_id)

    clear_storage(session_id)

    return Success(message='Wiped')
