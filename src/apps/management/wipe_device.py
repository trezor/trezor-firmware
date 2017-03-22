from trezor import ui
from trezor.utils import unimport


@unimport
async def layout_wipe_device(session_id, msg):
    from trezor.messages.Success import Success
    from trezor.ui.text import Text
    from ..common.confirm import hold_to_confirm
    from ..common import storage

    await hold_to_confirm(session_id, Text(
        'WIPE DEVICE',
        ui.ICON_WIPE,
        ui.NORMAL, 'Do you really want to', 'wipe the device?',
        ui.NORMAL, '', 'All data will be lost.'))

    storage.wipe()

    return Success(message='Device wiped')
