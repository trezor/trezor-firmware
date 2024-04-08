from typing import TYPE_CHECKING

import trezorui2
from trezor import log, ui, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import ActionCancelled, context

if TYPE_CHECKING:
    from typing import Awaitable, Callable, TypeVar

    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]

    InfoFunc = Callable[[], Awaitable[None]]

    T = TypeVar("T")


async def _button_request(
    br_type: str,
    code: ButtonRequestType = ButtonRequestType.Other,
    pages: int = 0,
) -> None:
    workflow.close_others()
    if __debug__:
        log.debug(__name__, "ButtonRequest.type=%s", br_type)
    await context.maybe_call(ButtonRequest(code=code, pages=pages or None), ButtonAck)


async def interact(
    layout_obj: ui.LayoutObj[T],
    br_type: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType | None = ActionCancelled,
) -> T:
    # shut down other workflows to prevent them from interfering with the current one
    workflow.close_others()
    # start the layout
    layout = ui.Layout(layout_obj)
    layout.start()
    # send the button request
    if br_type is not None:
        await _button_request(br_type, br_code, layout_obj.page_count())
    # wait for the layout result
    result = await context.wait(layout.get_result())
    # raise an exception if the user cancelled the action
    if raise_on_cancel is not None and result is trezorui2.CANCELLED:
        raise raise_on_cancel
    return result


def raise_if_not_confirmed(
    layout_obj: ui.LayoutObj[ui.UiResult],
    br_type: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    exc: ExceptionType = ActionCancelled,
) -> Awaitable[None]:
    action = interact(layout_obj, br_type, br_code, exc)
    return action  # type: ignore [Type cannot be assigned to type "None"]
