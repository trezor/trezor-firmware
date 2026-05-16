from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ApplyFlags, Success


async def apply_flags(msg: ApplyFlags) -> Success:
    from storage.device import set_flags
    from trezor.messages import Success

    from apps.common.device import require_initialized

    require_initialized()
    set_flags(msg.flags)
    return Success(message="Flags applied")
