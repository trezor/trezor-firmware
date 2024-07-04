from typing import TYPE_CHECKING

import trezorui2
from trezor import ui, utils, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest
from trezor.wire import ActionCancelled, context

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
    await context.maybe_call(
        ButtonRequest(code=code, pages=pages or None, name=br_name), ButtonAck
    )


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
    if raise_on_cancel is not None and result is trezorui2.CANCELLED:
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
) -> None:
    send_button_request = True

    while True:
        result = await interact(
            main_layout, br_name if send_button_request else None, br_code
        )
        # raises on cancel
        send_button_request = False

        if result is trezorui2.CONFIRMED:
            return
        elif result is trezorui2.INFO:
            await interact(info_layout, None, raise_on_cancel=None)
            continue
        else:
            raise RuntimeError  # unexpected result


def draw_simple(layout: trezorui2.LayoutObj[Any]) -> None:
    # Simple drawing not supported for layouts that set timers.
    def dummy_set_timer(token: int, duration: int) -> None:
        raise RuntimeError

    layout.attach_timer_fn(dummy_set_timer, None)
    if utils.USE_BACKLIGHT:
        ui.backlight_fade(ui.BacklightLevels.DIM)
    if layout.paint():
        ui.refresh()
    if utils.USE_BACKLIGHT:
        ui.backlight_fade(ui.BacklightLevels.NORMAL)
