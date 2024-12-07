from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import FirmwareHash, GetFirmwareHash


async def get_firmware_hash(msg: GetFirmwareHash) -> FirmwareHash:
    from trezor import wire, workflow
    from trezor.messages import FirmwareHash
    from trezor.ui.layouts.progress import progress
    from trezor.utils import firmware_hash

    workflow.close_others()
    progress_obj = progress()

    def report(progress: int, total: int) -> None:
        progress_obj.report(1000 * progress // total)

    try:
        hash = firmware_hash(msg.challenge, report)
    except ValueError as e:
        raise wire.DataError(str(e))

    return FirmwareHash(hash=hash)
