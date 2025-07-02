from typing import TYPE_CHECKING

import trezorui_api
from trezor.enums import ButtonRequestType
from trezor.ui.layouts.common import interact

if TYPE_CHECKING:
    from trezorui_api import LayoutObj, UiResult
    from typing_extensions import Self


class Menu:
    def __init__(self, name: str, *children: "Details") -> None:
        self.name = name
        self.children = children

    @classmethod
    def root(cls, *children: "Details") -> Self:
        return cls("", *children)


class Details:
    def __init__(self, name: str, *properties: "Property") -> None:
        self.name = name
        self.properties = properties


class Property:
    def __init__(self, name: str | None, value: str, is_data: bool = False) -> None:
        self.name = name
        self.value = value
        self.is_data = is_data

    @classmethod
    def data(cls, name: str | None, value: str) -> Self:
        return cls(name, value, True)


async def show_menu(
    root: Menu,
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
) -> None:
    menu_path = []
    current_page = 0
    while True:
        menu = root
        for i in menu_path:
            menu = menu.children[i]

        if isinstance(menu, Menu):
            layout = trezorui_api.select_menu(
                items=[child.name for child in menu.children], page_counter=current_page
            )
        else:
            layout = trezorui_api.show_properties(
                title=menu.name,
                properties=[
                    (item.name, item.value, item.is_data) for item in menu.properties
                ],
            )

        choice = await interact(layout, br_name, br_code, raise_on_cancel=None)
        if isinstance(choice, int):
            menu_path.append(choice)
            current_page = 0
            continue

        if menu_path:
            current_page = menu_path.pop()
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
