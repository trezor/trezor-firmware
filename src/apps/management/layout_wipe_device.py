from trezor import ui
from trezor.utils import unimport


@unimport
async def layout_wipe_device(message, session_id):
    from trezor.messages.Success import Success
    from trezor.ui.text import Text
    from ..common.confirm import hold_to_confirm
    from ..common import storage

    ui.display.clear()

    content = Text(
        'Wiping device',
        ui.BOLD, 'Do you really want to', 'wipe the device?',
        ui.NORMAL, '', 'All data will be lost.')
    await hold_to_confirm(session_id, content)

    storage.clear(session_id)

    return Success(message='Device wiped')
