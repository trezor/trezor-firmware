from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.messages import (
        Success,
        Disconnect,
    )


async def disconnect(ctx: GenericContext, _msg: Disconnect) -> Success:
    from trezor.messages import (
        Success,
    )
    from trezor.ui.layouts import confirm_action

    await confirm_action(ctx, None, "DISCONNECT")

    ble.disconnect()

    return Success()
