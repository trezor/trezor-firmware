from trezor import log, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

if False:
    from typing import Any, Awaitable, Optional, Tuple, Type, Union

    LayoutType = Awaitable[Any]
    PropertyType = Tuple[Optional[str], Union[str, bytes, None]]
    ExceptionType = Union[BaseException, Type[BaseException]]


if __debug__:
    from ..components.tt.scroll import Paginated


async def interact(
    ctx: wire.GenericContext,
    layout: LayoutType,
    brtype: str,
    brcode: ButtonRequestType = ButtonRequestType.Other,
) -> Any:
    log.debug(__name__, "ButtonRequest.type={}".format(brtype))
    if layout.__class__.__name__ == "Paginated":
        assert isinstance(layout, Paginated)
        return await layout.interact(ctx, code=brcode)
    else:
        workflow.close_others()
        await ctx.call(ButtonRequest(code=brcode), ButtonAck)
        return await ctx.wait(layout)
