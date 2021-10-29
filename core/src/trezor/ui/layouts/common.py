from trezor import log, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

if False:
    from typing import Any, Awaitable, Optional, Tuple, Type, Union

    LayoutType = Awaitable[Any]
    PropertyType = Tuple[Optional[str], Union[str, bytes, None]]
    ExceptionType = Union[BaseException, Type[BaseException]]


if __debug__:
    from trezor import utils

    if utils.MODEL == "T":
        from ..components.tt.scroll import Paginated


async def button_request(
    ctx: wire.GenericContext,
    br_type: str,
    code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    if __debug__:
        log.debug(__name__, "ButtonRequest.type=%s", br_type)
    workflow.close_others()
    await ctx.call(ButtonRequest(code=code), ButtonAck)


async def interact(
    ctx: wire.GenericContext,
    layout: LayoutType,
    br_type: str,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> Any:
    if layout.__class__.__name__ == "Paginated":
        assert isinstance(layout, Paginated)
        return await layout.interact(ctx, code=br_code)
    else:
        await button_request(ctx, br_type, br_code)
        return await ctx.wait(layout)
