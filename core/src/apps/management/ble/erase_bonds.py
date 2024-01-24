from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BLEEraseBonds, Success


async def erase_bonds(_msg: BLEEraseBonds) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action("ble_erase_bonds", "ERASE BONDS")

    ble.erase_bonds()

    return Success()
