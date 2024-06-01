from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import FirmwareHash, GetFirmwareHash


async def get_firmware_hash(msg: GetFirmwareHash) -> FirmwareHash:
    from trezor import io, wire, workflow
    from trezor.messages import FirmwareHash
    from trezor.ui.layouts.progress import progress

    workflow.close_others()
    progress_obj = progress()

    try:
        area = io.flash_area.FIRMWARE
        area_size = area.size()

        def report(byte: int) -> None:
            progress_obj.report(1000 * byte // area_size)

        hash = area.hash(0, area.size(), msg.challenge, report)
    except ValueError as e:
        raise wire.DataError(str(e))

    return FirmwareHash(hash=hash)
