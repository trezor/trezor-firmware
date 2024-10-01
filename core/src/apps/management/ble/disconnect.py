from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Disconnect, Success


async def disconnect(_msg: Disconnect) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    await confirm_action("disconnect", "DISCONNECT")

    ctx = get_context()

    await ctx.write(Success(message="Erasing"))

    ble.disconnect()

    raise RuntimeError
