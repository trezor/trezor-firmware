from typing import TYPE_CHECKING

import trezorui_api
from trezor import ui, workflow
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, Coroutine, Literal, TypeVar, overload

    from trezorui_api import PropertyType, StrPropertyType  # noqa: F401

    ExceptionType = BaseException | type[BaseException]

    InfoFunc = Callable[[], Awaitable[None]]

    T = TypeVar("T")

    @overload
    async def interact(
        layout_obj: ui.LayoutObj[Any],
        br_name: str | None,
        br_code: ButtonRequestType = ButtonRequestType.Other,
        raise_on_cancel: ExceptionType | None = ActionCancelled,
        *,
        confirm_only: Literal[True],
    ) -> None: ...

    @overload
    async def interact(
        layout_obj: ui.LayoutObj[T],
        br_name: str | None,
        br_code: ButtonRequestType = ButtonRequestType.Other,
        raise_on_cancel: ExceptionType | None = ActionCancelled,
        *,
        confirm_only: bool = False,
    ) -> T: ...


async def interact(
    layout_obj: ui.LayoutObj[T],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType | None = ActionCancelled,
    *,
    confirm_only: bool = False,
) -> T | None:
    """Return the result of user interaction with the layout.

    If the result is CANCELLED, raise the specified exception (`ActionCancelled`
    by default), unless `raise_on_cancel` is explicitly set to None.

    Specify `confirm_only=True` to invoke "raise if not confirmed" behavior,
    that is:
    * if the result is CONFIRMED, return None
    * if the result is CANCELLED, raise the `raise_on_cancel` exception
    * on any other result (indicating a bug in the caller), raise a RuntimeError
    Setting `raise_on_cancel=None` together with `confirm_only=True` invalid,
    and a RuntimeError will be raised in the cancel case.
    """
    # shut down other workflows to prevent them from interfering with the current one
    workflow.close_others()
    # start the layout
    layout = ui.Layout(layout_obj)
    layout.start()
    if br_name is not None:
        # store the first button request to be sent
        layout.button_request_box.put((br_code, br_name))
    # wait for the layout result
    result = await layout.get_result()

    # raise an exception if the user cancelled the action
    if raise_on_cancel is not None and result is trezorui_api.CANCELLED:
        raise raise_on_cancel

    if confirm_only:
        # raise_if_not_confirmed behavior: return None if the user confirmed the action
        if result is trezorui_api.CONFIRMED:
            return None
        # if the result was CANCELLED, the earlier branch should have raised
        # ...raise otherwise
        raise RuntimeError  # unexpected result

    return result


def raise_if_not_confirmed(
    layout_obj: ui.LayoutObj[ui.UiResult],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    exc: ExceptionType = ActionCancelled,
) -> Coroutine[Any, Any, None]:
    return interact(layout_obj, br_name, br_code, exc, confirm_only=True)


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


async def confirm_linear_flow(
    *confirm_factories: Callable[[], Awaitable[ui.UiResult]],
    confirm_cancel_factory: Callable[[], LayoutObj[ui.UiResult]] | None,
) -> None:
    i = 0
    while i < len(confirm_factories):
        layout = confirm_factories[i]()
        res = await layout
        if res is trezorui_api.CONFIRMED:
            i += 1
        elif res is trezorui_api.CANCELLED:
            if confirm_cancel_factory is None:
                raise ActionCancelled
            else:
                cancel_layout = ui.Layout(confirm_cancel_factory())
                layout.start()
                cancel_res = await cancel_layout.get_result()
                if cancel_res is trezorui_api.CONFIRMED:
                    raise ActionCancelled
                else:
                    continue
        elif res is trezorui_api.BACK and i > 0:
            i -= 1
        else:
            raise ActionCancelled


def draw_simple(layout: trezorui_api.LayoutObj[Any]) -> None:
    ui.Layout(layout).start()
