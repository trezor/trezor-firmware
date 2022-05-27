from typing import TYPE_CHECKING

from trezor import log, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

if TYPE_CHECKING:
    from typing import Any, Awaitable

    LayoutType = Awaitable[Any]
    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]


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
        from ..components.tt.scroll import Paginated

        assert isinstance(layout, Paginated)
        return await layout.interact(ctx, code=br_code)
    else:
        await button_request(ctx, br_type, br_code)
        return await ctx.wait(layout)
