from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BLEDisconnect, Success


async def disconnect(_msg: BLEDisconnect) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action("ble_disconnect", "DISCONNECT")

    ble.disconnect()

    return Success()
