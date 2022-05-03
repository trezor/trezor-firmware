from micropython import const
from typing import TYPE_CHECKING

from trezor import utils, wire, workflow
from trezor.messages import FirmwareChunk, FirmwareChunkAck, GetFirmware, Success
from trezor.ui.layouts import confirm_action, draw_simple_text

from .get_firmware_hash import _render_progress

if TYPE_CHECKING:
    from trezor.wire import Context

CHUNK_SIZE = const(1024 * 4)
# assuming that all sectors are of size 128 kB
PROGRESS_TOTAL = utils.FIRMWARE_SECTORS_COUNT * 128 * 1024


async def get_firmware(ctx: Context, _msg: GetFirmware) -> Success:
    await confirm_action(
        ctx,
        "dump_firmware",
        title="Extract firmware",
        action="Do you want to extract device firmware?",
        description="Your seed will not be revealed.",
    )
    sector_buffer = bytearray(CHUNK_SIZE)
    packet = FirmwareChunk(chunk=sector_buffer)

    workflow.close_others()
    draw_simple_text("Please wait")

    progress = 0
    _render_progress(progress, PROGRESS_TOTAL)
    for i in range(utils.FIRMWARE_SECTORS_COUNT):
        size = utils.firmware_sector_size(i)
        try:
            for ofs in range(0, size, CHUNK_SIZE):
                utils.get_firmware_chunk(i, ofs, sector_buffer)
                await ctx.call(packet, FirmwareChunkAck)
                progress += CHUNK_SIZE
                _render_progress(progress, PROGRESS_TOTAL)
            # reset progress to known point, in case some sectors are not 128 kB
            progress = (i + 1) * 128 * 1024
            _render_progress(progress, PROGRESS_TOTAL)
        except ValueError:
            raise wire.DataError("Failed to dump firmware.")
    return Success(message="Firmware dumped.")
