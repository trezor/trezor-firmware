from typing import TYPE_CHECKING, Awaitable

import trezorui_api
from trezor.enums import ButtonRequestType
from trezor.ui.layouts.common import interact
from trezor.wire import ActionCancelled

if TYPE_CHECKING:
    from typing import Callable, Iterable, Sequence, TypeVar

    from typing_extensions import Self

    from common import ExceptionType

    T = TypeVar("T")


async def _cancel_default() -> trezorui_api.UiResult:
    return trezorui_api.CONFIRMED


class Menu:
    def __init__(
        self,
        name: str,
        children: Sequence["Details"],
        cancel: "Cancel | None" = None,
    ) -> None:
        self.name = name
        self.children = children
        self.cancel = cancel

    @classmethod
    def root(
        cls, children: Iterable["Details"] = (), cancel: "str | Cancel | None" = None
    ) -> Self:
        if isinstance(cancel, str):
            cancel = Cancel(cancel, _cancel_default)
        return cls("", children=tuple(children), cancel=cancel)


class Details:
    def __init__(self, name: str, factory: Callable[[], Awaitable[T]]) -> None:
        self.name = name
        self.factory = factory

    @classmethod
    def from_layout(
        cls, name: str, layout_factory: Callable[[], trezorui_api.LayoutObj[T]]
    ) -> Self:
        return cls(
            name,
            lambda: interact(layout_factory(), br_name=None, raise_on_cancel=None),
        )


class Cancel(Details):
    pass


async def show_menu(
    root: Menu,
    raise_on_cancel: ExceptionType = ActionCancelled,
) -> None:
    menu_path = []
    current_item = 0
    while True:
        menu = root
        for i in menu_path:
            menu = menu.children[i]

        if isinstance(menu, Menu):
            layout = trezorui_api.select_menu(
                items=[child.name for child in menu.children],
                current=current_item,
                cancel=menu.cancel and menu.cancel.name,
            )
            choice = await interact(layout, br_name=None, raise_on_cancel=None)
            if choice is trezorui_api.CANCELLED:
                if menu.cancel:
                    result = await menu.cancel.factory()
                    assert result in (trezorui_api.CONFIRMED, trezorui_api.CANCELLED)
                    if result is trezorui_api.CONFIRMED:
                        # cancellation is confirmed - raise an exception
                        raise raise_on_cancel
                    # cancellation is not confirmed - back to the menu
                    continue
            elif isinstance(choice, int):
                # go one level down
                menu_path.append(choice)
                current_item = 0
                continue
        else:
            assert isinstance(menu, Details)
            # Details' layout is created on-demand (saving memory)
            await menu.factory()  # the result is ignored

        # go one level up, or exit the menu
        if menu_path:
            current_item = menu_path.pop()
        else:
            return


async def confirm_with_menu(
    main: trezorui_api.LayoutObj[trezorui_api.UiResult],
    menu: Menu,
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType = ActionCancelled,
) -> None:
    while True:
        result = await interact(main, br_name, br_code, raise_on_cancel)
        br_name = None  # ButtonRequest should be sent once (for the main layout)
        if result is trezorui_api.INFO:
            await show_menu(menu, raise_on_cancel)
        else:
            break
