from typing import TYPE_CHECKING

from trezor import log, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import context

if TYPE_CHECKING:
    from typing import Any, Awaitable, Protocol

    LayoutType = Awaitable[Any]
    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]

    class ProgressLayout(Protocol):
        def report(self, value: int, description: str | None = None) -> None:
            ...


async def button_request(
    br_type: str,
    code: ButtonRequestType = ButtonRequestType.Other,
    pages: int | None = None,
) -> None:
    if __debug__:
        log.debug(__name__, "ButtonRequest.type=%s", br_type)
    workflow.close_others()
    await context.maybe_call(ButtonRequest(code=code, pages=pages), ButtonAck)


async def interact(
    layout: LayoutType,
    br_type: str,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> Any:
    pages = None
    if hasattr(layout, "page_count") and layout.page_count() > 1:  # type: ignore [Cannot access member "page_count" for type "LayoutType"]
        # We know for certain how many pages the layout will have
        pages = layout.page_count()  # type: ignore [Cannot access member "page_count" for type "LayoutType"]
    await button_request(br_type, br_code, pages)
    return await context.wait(layout)
