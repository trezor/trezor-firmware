from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetFirmwareHash, FirmwareHash
    from trezor.wire import Context


async def get_firmware_hash(ctx: Context, msg: GetFirmwareHash) -> FirmwareHash:
    from trezor.messages import FirmwareHash
    from trezor.utils import firmware_hash
    from trezor.ui.layouts import draw_simple_text
    from trezor import wire, workflow

    workflow.close_others()
    draw_simple_text("Please wait")

    try:
        hash = firmware_hash(msg.challenge, _render_progress)
    except ValueError as e:
        raise wire.DataError(str(e))

    return FirmwareHash(hash=hash)


def _render_progress(progress: int, total: int) -> None:
    from trezor.utils import DISABLE_ANIMATION
    from trezor import ui

    if not DISABLE_ANIMATION:
        p = 1000 * progress // total
        ui.display.loader(p, False, 18, ui.WHITE, ui.BG)
        ui.refresh()
