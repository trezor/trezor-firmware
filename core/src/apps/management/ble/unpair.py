from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Success, Unpair


async def unpair(_msg: Unpair) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    await confirm_action("Unpair current device", "Unpair")

    ctx = get_context()

    await ctx.write(Success(message="Erasing"))

    ble.unpair()

    raise RuntimeError
