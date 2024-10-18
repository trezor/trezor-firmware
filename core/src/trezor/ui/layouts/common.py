from typing import TYPE_CHECKING

import trezorui_api
from trezor import ui, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import ActionCancelled, context

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, TypeVar

    PropertyType = tuple[str | None, str | bytes | None]
    ExceptionType = BaseException | type[BaseException]

    InfoFunc = Callable[[], Awaitable[None]]

    T = TypeVar("T")


async def _button_request(
    br_name: str,
    code: ButtonRequestType = ButtonRequestType.Other,
    pages: int = 0,
) -> None:
    workflow.close_others()
    if __debug__:
        log.info(__name__, "ButtonRequest sent: %s", br_name)
    await context.maybe_call(
        ButtonRequest(code=code, pages=pages or None, name=br_name), ButtonAck
    )
    if __debug__:
        log.info(__name__, "ButtonRequest acked: %s", br_name)


async def interact(
    layout_obj: ui.LayoutObj[T],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType | None = ActionCancelled,
) -> T:
    # shut down other workflows to prevent them from interfering with the current one
    workflow.close_others()
    # start the layout
    layout = ui.Layout(layout_obj)
    layout.start()
    # send the button request
    if br_name is not None:
        await _button_request(br_name, br_code, layout_obj.page_count())
    # wait for the layout result
    result = await layout.get_result()
    # raise an exception if the user cancelled the action
    if raise_on_cancel is not None and result is trezorui_api.CANCELLED:
        raise raise_on_cancel
    return result


def raise_if_not_confirmed(
    layout_obj: ui.LayoutObj[ui.UiResult],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    exc: ExceptionType = ActionCancelled,
) -> Awaitable[None]:
    action = interact(layout_obj, br_name, br_code, exc)
    return action  # type: ignore ["UiResult" is incompatible with "None"]


async def with_info(
    main_layout: ui.LayoutObj[ui.UiResult],
    info_layout: ui.LayoutObj[Any],
    br_name: str,
    br_code: ButtonRequestType,
    repeat_button_request: bool = False,  # TODO this should eventually always be true
    info_layout_can_confirm: bool = False,  # whether the info layout is allowed to confirm the whole flow
) -> None:
    first_br = br_name
    next_br = br_name if repeat_button_request else None

    # if repeat_button_request is True:
    #  * `first_br` (br_name) is sent on first interaction
    #  * `next_br` (br_name) is sent on the info screen
    #  * `first_br` is updated to `next_br` (still br_name) and that is sent for every
    #    subsequent interaction
    # if repeat_button_request is False:
    #  * `first_br` (br_name) is sent on first interaction
    #  * `next_br` (None) is sent on the info screen
    #  * `first_br` is cleared to None for every subsequent interaction
    while True:
        result = await interact(main_layout, first_br, br_code)
        # raises on cancel

        first_br = next_br

        if result is trezorui_api.CONFIRMED:
            return
        elif result is trezorui_api.INFO:
            info_result = await interact(
                info_layout, next_br, br_code, raise_on_cancel=None
            )
            if info_layout_can_confirm and info_result is trezorui_api.CONFIRMED:
                return
            else:
                # no matter what the info layout returns, we always go back to the main layout
                continue
        else:
            raise RuntimeError  # unexpected result


def draw_simple(layout: trezorui_api.LayoutObj[Any]) -> None:
    ui.Layout(layout).start()
