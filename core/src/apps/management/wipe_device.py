import storage
from trezor.messages.Success import Success

from apps.common.confirm import require_interact


async def wipe_device(ctx, msg):
    await require_interact(ctx, "confirm_wipe")

    storage.wipe()

    return Success(message="Device wiped")
