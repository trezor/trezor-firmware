from trezor import ui
from trezor.utils import unimport


@unimport
async def layout_wipe_device(message, session_id):
    from trezor.messages.Success import Success
    from trezor.ui.text import Text
    from .confirm import hold_to_confirm
    from .storage import clear_storage

    ui.display.clear()

    content = Text('Wiping device',
                   ui.BOLD, 'Do you really want to', 'wipe the device?',
                   ui.NORMAL, '', 'All data will be lost.')
    await hold_to_confirm(session_id, content)

    clear_storage(session_id)

    return Success(message='Wiped')
