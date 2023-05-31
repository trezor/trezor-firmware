from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ShowDeviceTutorial, Success
    from trezor.wire import Context


async def show_tutorial(ctx: Context, msg: ShowDeviceTutorial) -> Success:
    from trezor.messages import Success

    # NOTE: tutorial is defined only for TR, and this function should
    # also be called only in case of TR
    from trezor.ui.layouts import tutorial

    await tutorial(ctx)

    return Success(message="Tutorial shown")
