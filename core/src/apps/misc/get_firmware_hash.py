from typing import TYPE_CHECKING

from trezor import wire
from trezor.messages import FirmwareHash, GetFirmwareHash
from trezor.utils import firmware_hash

if TYPE_CHECKING:
    from trezor.wire import Context


async def get_firmware_hash(ctx: Context, msg: GetFirmwareHash) -> FirmwareHash:
    try:
        hash = firmware_hash(msg.challenge)
    except ValueError as e:
        raise wire.DataError(str(e))

    return FirmwareHash(hash=hash)
