from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BLEComparisonRequest, Success


async def comparison_request(msg: BLEComparisonRequest) -> Success:
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire import context

    await context.with_context(
        None,
        confirm_action(
            "", "DO THE NUMBERS MATCH?", description=msg.key.decode("utf-8")
        ),
    )

    return Success()
