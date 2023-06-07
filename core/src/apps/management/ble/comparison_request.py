from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import GenericContext
    from trezor.messages import (
        Success,
        ComparisonRequest,
    )


async def comparison_request(ctx: GenericContext, msg: ComparisonRequest) -> Success:
    from trezor.messages import (
        Success,
    )
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        ctx, None, "DO THE NUMBERS MATCH?", description=msg.key.decode("utf-8")
    )

    return Success()
