from typing import TYPE_CHECKING

from trezor import workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import context

if TYPE_CHECKING:
    from typing import Awaitable, Protocol, TypeVar

    T = TypeVar("T")

    LayoutType = Awaitable
    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]

    class ProgressLayout(Protocol):
        def report(self, value: int, description: str | None = None) -> None: ...


async def button_request(
    br_name: str,
    code: ButtonRequestType = ButtonRequestType.Other,
    pages: int | None = None,
) -> None:
    workflow.close_others()
    await context.maybe_call(
        ButtonRequest(code=code, pages=pages, name=br_name), ButtonAck
    )


async def interact(
    layout: LayoutType[T],
    br_name: str,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> T:
    pages = None
    if hasattr(layout, "page_count") and layout.page_count() > 1:  # type: ignore [Cannot access attribute "page_count" for class "LayoutType"]
        # We know for certain how many pages the layout will have
        pages = layout.page_count()  # type: ignore [Cannot access attribute "page_count" for class "LayoutType"]
    await button_request(br_name, br_code, pages)
    return await layout
