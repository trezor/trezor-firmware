from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import RepairRequest, Success


async def repair_request(_msg: RepairRequest) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action(None, "RE-PAIR DEVICE")

    return Success()
