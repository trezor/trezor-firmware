from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BLERepairRequest, Success


async def repair_request(_msg: BLERepairRequest) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire import context

    await context.with_context(None, confirm_action("", "RE-PAIR DEVICE"))

    return Success()
