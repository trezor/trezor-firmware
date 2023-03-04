from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.messages import (
        Success,
        RepairRequest,
    )


async def repair_request(ctx: GenericContext, _msg: RepairRequest) -> Success:
    from trezor.messages import (
        Success,
    )
    from trezor.ui.layouts import confirm_action

    await confirm_action(ctx, None, "RE-PAIR DEVICE")

    return Success()
