from typing import TYPE_CHECKING, Awaitable

import trezorui_api
from trezor.enums import ButtonRequestType
from trezor.ui import Layout
from trezor.ui.layouts.common import interact
from trezor.wire import ActionCancelled

if TYPE_CHECKING:
    from typing import Callable, Generic, Iterable, Sequence, TypeVar, overload

    from typing_extensions import Self, TypeAlias

    from .common import ExceptionType

    T = TypeVar("T")
    # value produced by a menu leaf and propagated out of the tree
    R = TypeVar("R")

    # a node of the menu tree: either a subtree, or a leaf
    MenuNode: TypeAlias = "Menu[R] | MenuLeaf[R]"
else:
    R = 0
    Generic = {R: object}


async def _cancel_default() -> trezorui_api.UiResult:
    return trezorui_api.CONFIRMED


class Menu(Generic[R]):
    def __init__(
        self,
        name: str,
        children: "Sequence[MenuNode[R]]",
        cancel: "Cancel | None" = None,
    ) -> None:
        self.name = name
        self.children = children
        self.cancel = cancel

    @classmethod
    def root(
        cls,
        children: "Iterable[MenuNode[R]]" = (),
        cancel: "str | Cancel | None" = None,
    ) -> Self:
        if isinstance(cancel, str):
            cancel = Cancel(cancel, _cancel_default)
        return cls("", children=tuple(children), cancel=cancel)


class MenuLeaf(Generic[R]):
    """A leaf node of the menu tree.

    `interact()` returns `None` to indicate that the menu tree should be resumed
    (one level up), or a value of type `R`, which is propagated out of the whole
    tree by `show_menu()`.
    """

    # `Cancel` overrides this: its result is consumed by `show_menu()` itself.
    _RETURN_RESULT = False

    def __init__(self, name: str, interact: Callable[[], Awaitable[R | None]]) -> None:
        self.name = name
        self._interact = interact

    @classmethod
    def from_layout(
        cls,
        name: str,
        layout_factory: Callable[[], trezorui_api.LayoutContext[R]],
        *,
        return_result: bool | None = None,
        br_name: str | None = None,
        br_code: ButtonRequestType = ButtonRequestType.Other,
        raise_on_cancel: ExceptionType | None = None,
    ) -> Self:
        """IMPORTANT: `layout_factory()` MUST create a new layout on each invocation.

        Unless `return_result` is set, the layout's result is discarded and the menu
        tree is resumed. Otherwise the result is returned by `show_menu()`, so
        `layout_factory()` must produce a layout whose result type matches the tree's.
        """
        propagate = cls._RETURN_RESULT if return_result is None else return_result

        async def _interact() -> R | None:
            with layout_factory() as obj:
                # the leaf's layout is de-allocated after interact() returns.
                result = await interact(obj, br_name, br_code, raise_on_cancel)
            return result if propagate else None

        return cls(name, _interact)


class Cancel(MenuLeaf):
    """Cancel-confirmation node; its result is consumed by `show_menu()` itself."""

    _RETURN_RESULT = True


class MenuResult(Generic[R]):
    """A value produced by a menu leaf, paired with the leaf that produced it."""

    def __init__(self, leaf: "MenuLeaf[R]", value: R) -> None:
        self.leaf = leaf
        self.value = value


async def show_menu(
    root: Menu[R],
    raise_on_cancel: ExceptionType = ActionCancelled,
) -> MenuResult[R] | None:
    """Walk the menu tree until a leaf produces a value, or the user leaves the root.

    Returns the leaf and the value it produced, so that the caller can tell the
    leaves apart, or `None` if the tree was left without producing a value.
    """
    menu_path = []
    current_item = 0
    while True:
        menu: MenuNode[R] = root
        for i in menu_path:
            assert isinstance(menu, Menu)
            menu = menu.children[i]

        if isinstance(menu, Menu):
            with trezorui_api.select_menu(
                items=[child.name for child in menu.children],
                current=current_item,
                cancel=menu.cancel and menu.cancel.name,
            ) as layout:
                choice = await interact(layout, br_name=None, raise_on_cancel=None)

            if choice is trezorui_api.CANCELLED:
                if menu.cancel:
                    result = await menu.cancel._interact()
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
            # the leaf's layout is created on-demand (saving memory)
            leaf_result = await menu._interact()
            if leaf_result is not None:
                # the leaf produced a value - leave the whole tree
                return MenuResult(menu, leaf_result)

        # go one level up, or exit the tree
        if menu_path:
            current_item = menu_path.pop()
        else:
            return None


if TYPE_CHECKING:
    # TEMPORARY COMPATIBILITY SHIM - to be removed.
    #
    # `interact_with_menu()` returns `T | MenuResult[R]`, but most call sites still
    # declare `-> UiResult` and hand the result straight back, so the union does not
    # typecheck there. Every one of them passes an info-only menu (`create_info_menu_leaf()`
    # leaves, which discard their layout's result), so the first overload keeps them
    # on the old plain-`T` typing while the second serves menus that do produce a
    # value.
    #
    # Drop both overloads once these call sites handle `MenuResult` themselves
    # (25 calls in total, all of them value-less menus today):
    #
    #   delizia:  confirm_action, confirm_value, confirm_ethereum_vault_tx (5),
    #             confirm_ethereum_vault_claim (3)
    #   eckhart:  confirm_output (2), confirm_trade, confirm_ethereum_tx,
    #             confirm_ethereum_vault_tx (5), confirm_ethereum_vault_claim (3),
    #             confirm_ethereum_staking_tx, confirm_solana_staking_tx (2)
    #
    # Note the overload is picked from the menu's *declared* type: annotating a
    # value-less menu as anything but `Menu[None]` pushes its caller onto the
    # second overload.

    @overload
    async def interact_with_menu(
        main: trezorui_api.LayoutObj[T],
        menu: "Menu[None]",
        br_name: str | None,
        br_code: ButtonRequestType = ButtonRequestType.Other,
        raise_on_cancel: ExceptionType = ActionCancelled,
        *,
        layout_type: type[Layout] = Layout,
    ) -> T:
        """The menu cannot produce a value, so only the main layout's result."""

    @overload
    async def interact_with_menu(
        main: trezorui_api.LayoutObj[T],
        menu: "Menu[R]",
        br_name: str | None,
        br_code: ButtonRequestType = ButtonRequestType.Other,
        raise_on_cancel: ExceptionType = ActionCancelled,
        *,
        layout_type: type[Layout] = Layout,
    ) -> T | MenuResult[R]:
        """Either the main layout's result, or a leaf and the value it produced."""


async def interact_with_menu(
    main: trezorui_api.LayoutObj[T],
    menu: Menu[R],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType = ActionCancelled,
    *,
    layout_type: type[Layout] = Layout,
) -> T | MenuResult[R]:
    while True:
        result = await interact(
            main, br_name, br_code, raise_on_cancel, layout_type=layout_type
        )
        br_name = None  # ButtonRequest should be sent once (for the main layout)
        if result is trezorui_api.INFO:
            menu_result = await show_menu(menu, raise_on_cancel)
            if menu_result is not None:
                return menu_result
            # the tree was left without a value - back to the main layout
        else:
            return result


async def confirm_with_menu(
    main: trezorui_api.LayoutObj[T],
    menu: Menu[None],
    br_name: str | None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType = ActionCancelled,
    *,
    layout_type: type[Layout] = Layout,
) -> None:
    """
    Make sure the layout result is CONFIRMED (or raises an exception).

    In order to handle other results (such as BACK), use `interact_with_menu`.
    """
    result = await interact_with_menu(
        main, menu, br_name, br_code, raise_on_cancel, layout_type=layout_type
    )
    # use this function when the layout may only return CONFIRMED on success (or raise an exception)
    assert result is trezorui_api.CONFIRMED
