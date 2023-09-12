from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, UploadBLEFirmwareChunk, UploadBLEFirmwareInit


async def upload_ble_firmware_chunk(msg: UploadBLEFirmwareChunk) -> int:
    result = ble.update_chunk(msg.data)

    return result


async def upload_ble_firmware_init(msg: UploadBLEFirmwareInit) -> Success:
    from trezor.enums import ButtonRequestType
    from trezor.messages import (
        Success,
        UploadBLEFirmwareChunk,
        UploadBLEFirmwareNextChunk,
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

    res = ble.update_init(msg.init_data, msg.binsize)

    await ctx.write(UploadBLEFirmwareNextChunk(offset=0))

    if res == 0:

        while True:

            received_msg = await ctx.read(
                (MessageType.UploadBLEFirmwareChunk,),
                UploadBLEFirmwareChunk,
            )

            result = await upload_ble_firmware_chunk(received_msg)

            upload_progress += len(received_msg.data)
            p = int(1000 * upload_progress / msg.binsize)
            progress_layout.report(p)

            if result == 0:
                result_msg = UploadBLEFirmwareNextChunk(offset=0)
                await ctx.write(result_msg)
                del (result_msg, received_msg)
            else:
                del received_msg
                break

    progress_layout.report(1000)

    return Success(message="BLE firmware update successful")
