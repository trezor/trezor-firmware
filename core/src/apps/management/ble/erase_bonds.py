from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EraseBonds, Success


async def erase_bonds(_msg: EraseBonds) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    await confirm_action("erase bonds", "ERASE BONDS")

    ctx = get_context()

    await ctx.write(Success(message="Erasing"))

    ble.erase_bonds()

    raise RuntimeError
