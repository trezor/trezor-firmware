from typing import TYPE_CHECKING

import trezorui_api
from trezor.enums import ButtonRequestType
from trezor.ui import Layout
from trezor.ui.layouts.common import interact
from trezor.wire import ActionCancelled

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Sequence
    from typing import Generic, overload

    from typing_extensions import Never, TypeAlias, TypeVar

    from .common import ExceptionType

    T = TypeVar("T")
    # value produced by a menu leaf and propagated out of the tree
    R = TypeVar("R", default=None, covariant=True)

    # a node of the menu tree: either a subtree, or a leaf
    MenuNode: TypeAlias = "Menu[R] | MenuLeaf[R]"
else:
    R = 0
    Generic = {R: object}


class Menu(Generic[R]):
    # a subtree is always an ordinary entry (see `MenuLeaf.intent`)
    intent = trezorui_api.MenuItemIntent.STANDARD

    def __init__(
        self,
        children: "Iterable[MenuNode[R]]" = (),
        name: str = "",
    ) -> None:
        self.name = name
        self.children: "Sequence[MenuNode[R]]" = tuple(children)


class MenuLeaf(Generic[R]):
    """A leaf node of the menu tree.

    `interact()` returns `None` to indicate that the menu tree should be resumed
    (one level up), or a value of type `R`, which is propagated out of the whole
    tree by `show_menu()`.
    """

    def __init__(
        self,
        name: str,
        interact: Callable[[], Awaitable[R | None]],
        *,
        intent: int = trezorui_api.MenuItemIntent.STANDARD,
    ) -> None:
        self.name = name
        self._interact = interact
        # what this entry means; each layout renders it in its own way
        self.intent = intent


def leaf_from_layout(
    name: str,
    layout_factory: Callable[[], trezorui_api.LayoutContext[R]],
    *,
    return_result: bool = False,
    intent: int = trezorui_api.MenuItemIntent.STANDARD,
    br_name: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Other,
    raise_on_cancel: ExceptionType | None = None,
) -> "MenuLeaf[R]":
    """IMPORTANT: `layout_factory()` MUST create a new layout on each invocation.

    Unless `return_result` is set, the layout's result is discarded and the menu
    tree is resumed. Otherwise the result is returned by `show_menu()`, so
    `layout_factory()` must produce a layout whose result type matches the tree's.

    `intent` is independent of what the leaf does: an entry may look dangerous
    and still produce a value rather than abort, as `cancel_leaf()` does.
    """

    async def _interact() -> "R | None":
        with layout_factory() as obj:
            # the leaf's layout is de-allocated after interact() returns.
            result = await interact(obj, br_name, br_code, raise_on_cancel)
        return result if return_result else None

    return MenuLeaf(name, _interact, intent=intent)


def cancel_leaf(
    name: str,
    exc: ExceptionType = ActionCancelled,
    *,
    confirm: "Callable[[], trezorui_api.LayoutContext[trezorui_api.UiResult]] | None" = None,
) -> "MenuLeaf[Never]":
    """A menu entry that aborts the workflow.

    Selecting it raises `exc`. If `confirm` is given, that layout is shown first
    and the workflow is aborted only if the user confirms it; otherwise the menu
    is resumed, as with any leaf that returns `None`.
    """

    async def _interact() -> None:
        if confirm is not None:
            with confirm() as obj:
                result = await interact(obj, br_name=None, raise_on_cancel=None)
            if result is not trezorui_api.CONFIRMED:
                return None  # declined - back to the menu
        raise exc

    return MenuLeaf(name, _interact, intent=trezorui_api.MenuItemIntent.DANGER)


class MenuResult(Generic[R]):
    """A value produced by a menu leaf, paired with the leaf that produced it."""

    def __init__(self, leaf: "MenuLeaf[R]", value: R) -> None:
        self.leaf = leaf
        self.value = value


async def show_menu(
    root: Menu[R],
) -> MenuResult[R] | None:
    """Walk the menu tree until a leaf produces a value, or the user leaves the root.

    Returns the leaf and the value it produced, so that the caller can tell the
    leaves apart, or `None` if the tree was left without producing a value.
    """
    menu_path: list[int] = []
    current_item = 0
    while True:
        menu: MenuNode[R] = root
        for i in menu_path:
            assert isinstance(menu, Menu)
            menu = menu.children[i]

        if isinstance(menu, Menu):
            with trezorui_api.select_menu(
                items=[(child.name, child.intent) for child in menu.children],
                current=current_item,
            ) as layout:
                choice = await interact(layout, br_name=None, raise_on_cancel=None)

            if isinstance(choice, int):
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
            menu_result = await show_menu(menu)
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
