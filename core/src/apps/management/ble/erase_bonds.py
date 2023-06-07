from trezorio import ble
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.messages import (
        Success,
        EraseBonds,
    )


async def erase_bonds(ctx: GenericContext, _msg: EraseBonds) -> Success:
    from trezor.messages import (
        Success,
    )
    from trezor.ui.layouts import confirm_action

    await confirm_action(ctx, None, "ERASE BONDS")

    ble.erase_bonds()

    return Success()
