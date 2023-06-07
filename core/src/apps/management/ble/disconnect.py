from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Disconnect, Success


async def disconnect(_msg: Disconnect) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action(None, "DISCONNECT")

    ble.disconnect()

    return Success()
