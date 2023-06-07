from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import EraseBonds, Success


async def erase_bonds(_msg: EraseBonds) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action(None, "ERASE BONDS")

    ble.erase_bonds()

    return Success()
