from typing import TYPE_CHECKING

import trezorui_api
from trezor.ui.layouts.common import interact

if TYPE_CHECKING:
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


async def show_menu(root: Menu) -> None:
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

        choice = await interact(layout, "menu", raise_on_cancel=None)
        if isinstance(choice, int):
            menu_path.append(choice)
            current_page = 0
            continue

        if menu_path:
            current_page = menu_path.pop()
        else:
            return
