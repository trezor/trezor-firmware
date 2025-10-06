from typing import TYPE_CHECKING

import trezorui_api
from trezor import ui, workflow
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, Coroutine, TypeVar

    from trezorui_api import PropertyType  # noqa: F401

    ExceptionType = BaseException | type[BaseException]

    InfoFunc = Callable[[], Awaitable[None]]

    T = TypeVar("T")


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
        layout.button_request_box.put((br_code, br_name))
    # wait for the layout result
    result = await layout.get_result()
    # raise an exception if the user cancelled the action
    if raise_on_cancel is not None and result is trezorui_api.CANCELLED:
        raise raise_on_cancel
    return result


def raise_if_cancelled(
    layout_obj: ui.LayoutObj[ui.UiResult],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    exc: ExceptionType = ActionCancelled,
) -> Coroutine[Any, Any, None]:
    action = interact(layout_obj, br_name, br_code, exc)
    return action  # type: ignore ["UiResult" is not assignable to "None"]


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
