from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ComparisonRequest, Success


async def comparison_request(msg: ComparisonRequest) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        None, "DO THE NUMBERS MATCH?", description=msg.key.decode("utf-8")
    )

    return Success()
