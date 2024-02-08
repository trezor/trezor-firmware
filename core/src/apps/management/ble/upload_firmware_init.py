from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BLEUploadFirmwareChunk, BLEUploadFirmwareInit, Success


async def upload_firmware_chunk(msg: BLEUploadFirmwareChunk) -> int:
    result = ble.update_chunk(msg.data)

    return result


async def upload_firmware_init(msg: BLEUploadFirmwareInit) -> Success:
    from trezor.enums import ButtonRequestType
    from trezor.messages import (
        BLEUploadFirmwareChunk,
        BLEUploadFirmwareNextChunk,
        Success,
    )
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        "confirm_upload_ble_firmware",
        "Upload BLE firmware",
        "",
        "Update BLE FW?\n",
        reverse=True,
        verb="Confirm",
        br_code=ButtonRequestType.Other,
    )

    from trezor.enums import MessageType
    from trezor.ui.layouts import progress
    from trezor.wire.context import get_context

    ctx = get_context()

    progress_layout = progress.progress("Uploading...")

    upload_progress = 0

    p = int(1000 * upload_progress / msg.binsize)
    progress_layout.report(p)

    finished = ble.update_init(msg.init_data, msg.binsize)
    while not finished:
        await ctx.write(BLEUploadFirmwareNextChunk())

        received_msg = await ctx.read(
            (MessageType.BLEUploadFirmwareChunk,),
            BLEUploadFirmwareChunk,
        )

        finished = await upload_firmware_chunk(received_msg)

        upload_progress += len(received_msg.data)
        p = int(1000 * upload_progress / msg.binsize)
        progress_layout.report(p)
        del received_msg

    progress_layout.report(1000)

    return Success(message="BLE firmware update successful")
