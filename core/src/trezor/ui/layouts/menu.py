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
    def __init__(self, name: str, *items: "Item") -> None:
        self.name = name
        self.items = items


class Item:
    def __init__(self, name: str | None, value: str, is_data: bool = False) -> None:
        self.name = name
        self.value = value
        self.is_data = is_data

    @classmethod
    def data(cls, name: str | None, value: str) -> Self:
        return cls(name, value, True)


async def show_menu(menu_items: Menu) -> None:
    menu_path = []
    current_page = 0
    while True:
        menu = menu_items
        for i in menu_path:
            menu = menu.children[i]

        if isinstance(menu, Menu):
            items = [child.name for child in menu.children]
            layout = trezorui_api.select_menu(items=items, page_counter=current_page)
        else:
            items = [(item.name, item.value, item.is_data) for item in menu.items]
            layout = trezorui_api.show_menu_items(title=menu.name, items=items)

        choice = await interact(layout, "menu", raise_on_cancel=None)
        if isinstance(choice, int):
            assert 0 <= choice < len(items)
            menu_path.append(choice)
            current_page = 0
            continue

        if menu_path:
            current_page = menu_path.pop()
        else:
            return
