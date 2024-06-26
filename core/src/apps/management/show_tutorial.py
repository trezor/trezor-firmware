from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ShowDeviceTutorial, Success


async def show_tutorial(msg: ShowDeviceTutorial) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import tutorial

    await tutorial()

    return Success(message="Tutorial shown")
