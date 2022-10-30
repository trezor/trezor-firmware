from typing import TYPE_CHECKING

from trezor import log, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

if TYPE_CHECKING:
    from typing import Any, Awaitable, Protocol

    LayoutType = Awaitable[Any]
    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]

    class ProgressLayout(Protocol):
        def report(self, value: int, description: str | None = None) -> None:
            ...


async def button_request(
    ctx: wire.GenericContext,
    br_type: str,
    code: ButtonRequestType = ButtonRequestType.Other,
    pages: int | None = None,
) -> None:
    if __debug__:
        log.debug(__name__, "ButtonRequest.type=%s", br_type)
    workflow.close_others()
    if pages is not None:
        await ctx.call(ButtonRequest(code=code, pages=pages), ButtonAck)
    else:
        await ctx.call(ButtonRequest(code=code), ButtonAck)


async def interact(
    ctx: wire.GenericContext,
    layout: LayoutType,
    br_type: str,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> Any:
    if hasattr(layout, "page_count") and layout.page_count() > 1:  # type: ignore [Cannot access member "page_count" for type "LayoutType"]
        await button_request(ctx, br_type, br_code, pages=layout.page_count())  # type: ignore [Cannot access member "page_count" for type "LayoutType"]
        return await ctx.wait(layout)
    else:
        await button_request(ctx, br_type, br_code)
        return await ctx.wait(layout)
