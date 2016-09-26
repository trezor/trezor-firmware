from trezor import ui
from trezor.utils import unimport


@unimport
async def layout_load_device(session_id, message):
    from trezor.messages.Success import Success
    from .confirm import require_confirm

    ui.clear()
    ui.display.text_center(
        120, 40, 'Really load device?', ui.BOLD, ui.WHITE, ui.BLACK)
    ui.display.text_center(
        120, 100, 'Never do this, please.', ui.NORMAL, ui.WHITE, ui.BLACK)

    await require_confirm(session_id)

    # TODO

    return Success(message='Loaded')
