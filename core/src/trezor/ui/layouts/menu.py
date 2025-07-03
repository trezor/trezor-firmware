from typing import TYPE_CHECKING

import trezorui_api
from trezor.enums import ButtonRequestType
from trezor.ui.layouts.common import interact

if TYPE_CHECKING:
    from typing import Any

    from trezorui_api import LayoutObj, UiResult
    from typing_extensions import Self


class Menu:
    def __init__(
        self, name: str, *children: "Details", cancel: str | None = None
    ) -> None:
        self.name = name
        self.children = children
        self.cancel = cancel

    @classmethod
    def root(cls, *children: "Details", cancel: str | None = None) -> Self:
        return cls("", *children, cancel=cancel)


class Details:
    def __init__(self, name: str, properties: "Properties") -> None:
        self.name = name
        self.value = properties.obj


class Properties:
    @classmethod
    def data(cls, value: str) -> Self:
        return cls(value)

    @classmethod
    def paragraphs(cls, value: list[tuple[str, str]]) -> Self:
        return cls(value)

    def __init__(self, obj: Any) -> None:
        """Internal c-tor: use the factory methods above instead."""
        self.obj = obj


async def show_menu(
    root: Menu,
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
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
                cancel=menu.cancel,
            )
        else:
            layout = trezorui_api.show_properties(
                title=menu.name,
                value=menu.value,
            )

        choice = await interact(layout, br_name, br_code, raise_on_cancel=None)
        if isinstance(choice, int):
            menu_path.append(choice)
            current_item = 0
            continue

        if menu_path:
            current_item = menu_path.pop()
        else:
            return


async def confirm_with_menu(
    main: LayoutObj[UiResult],
    menu: Menu,
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    while True:
        result = await interact(main, br_name, br_code)
        br_name = None  # ButtonRequest should be sent once (for the main layout)
        if result is trezorui_api.INFO:
            await show_menu(menu, br_name, br_code)
        else:
            break
