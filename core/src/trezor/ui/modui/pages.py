"""How a request becomes screens: its pages, its menu and its checks.

Each screen is one `trezormodui` call, and the model draws it; nothing here picks
a screen, a font or a button.
"""

from micropython import const
from typing import TYPE_CHECKING

import trezormodui
import trezorui_api
from trezor import TR, utils
from trezor.enums import ButtonRequestType
from trezor.ui.layouts.common import interact, raise_if_not_confirmed
from trezor.ui.layouts.menu import (
    Menu,
    MenuLeaf,
    MenuResult,
    cancel_leaf,
    interact_with_menu,
)
from trezormodui import DANGER, DATA, DETAILS, STRONG

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence
    from typing import TypeVar

    from trezormodui import Field as PageField
    from trezorui_api import LayoutObj, UiResult

    from . import Extra

    T = TypeVar("T")

    # A fact: `(kind, label, value)`, the label `None` for notes and warnings.
    # A `data` field's value is bytes in hand, or a source read while the person
    # pages.
    Field = tuple[int, str | None, "str | bytes | Source"]

# How long the closing screen stays up before it goes away.
_DONE_TIMEOUT_MS = const(3200)


class Source:
    """The bytes of a `data` field that are read while the person pages.

    `read(offset, length)` returns them. The pager reads in order, from the
    start, each range once, so a source may hash what it hands out: the bytes
    on the screen are then the bytes that get signed.
    """

    def __init__(
        self, total: int, read: "Callable[[int, int], Awaitable[bytes]]"
    ) -> None:
        self.total = total
        self.read = read


def check(
    fields: "Sequence[Field]", extras: "Sequence[Extra]", answer: int
) -> "list[Extra]":
    """The extras the request offers, once it is one the screens can draw.

    Every entry of the menu counts against its size: each offered extra, the way
    out, and "Show all" of a details answer. An extra with no facts is not
    offered. Each list of facts holds at most `MAX_DATA_FIELDS` data fields.
    Anything else raises `ValueError`.
    """
    offered = [extra for extra in extras if extra.fields]
    if len(offered) > trezormodui.max_extras(answer):
        raise ValueError("more extras than the menu has room for")
    _check_data(fields)
    for extra in offered:
        _check_data(extra.fields)
    return offered


def _check_data(facts: "Sequence[Field]") -> None:
    if sum(kind == DATA for kind, _, _ in facts) > trezormodui.MAX_DATA_FIELDS:
        raise ValueError("too many data fields")


class Pager:
    """The pages of a list of facts, the `data` field one chunk per page.

    `check` allows at most `MAX_DATA_FIELDS` (one) `data` field per list, so
    one offset pages it. A chunk is read only when its page is drawn, so a
    refusal between pages reads nothing more.
    """

    def __init__(self, fields: "Sequence[Field]") -> None:
        self.fields = fields
        self.offset = 0

    async def next(self) -> "tuple[list[PageField], bool]":
        """The next page, and whether it is the last."""
        page: list[PageField] = []
        last = True
        for kind, label, value in self.fields:
            if kind != DATA:
                assert isinstance(value, str)
                page.append((kind, label, value))
                continue
            offset = self.offset
            source = isinstance(value, Source)
            total = value.total if source else len(value)
            length = min(trezormodui.DATA_CHUNK_BYTES, total - offset)
            if source:
                chunk = await value.read(offset, length) if length else b""
            else:
                assert isinstance(value, bytes)
                chunk = value[offset : offset + length]
            self.offset = offset + length
            last = self.offset >= total
            page.append((kind, label, chunk))
        return page, last


async def paged(
    fields: "Sequence[Field]",
    show: "Callable[[list[PageField], bool, bool], Awaitable[T]]",
) -> "T":
    """Show the pages of `fields` until one is not confirmed, or the last is.

    `show(page, last, first)` draws one page and returns its result.
    """
    pager = Pager(fields)
    first = True
    while True:
        page, last = await pager.next()
        result = await show(page, last, first)
        if result is not trezorui_api.CONFIRMED or last:
            return result
        first = False


async def review(
    name: str,
    title: str,
    fields: "Sequence[Field]",
    extras: "Sequence[Extra]",
    answer: int,
) -> bool:
    """Show a review and wait for its answer.

    Returns `True` when the person picked "Show all" of a details answer, and
    `False` for a yes. A refusal raises `ActionCancelled`.
    """
    offered = check(fields, extras, answer)
    if answer == DANGER:
        await paged(fields, lambda page, last, first: _danger(name, title, page, first))
        return False

    menu = _menu(offered, answer == DETAILS)

    async def show(page: "list[PageField]", last: bool, first: bool) -> object:
        with trezormodui.review(
            title=title,
            fields=page,
            verb=None if last else TR.buttons__continue,
            hold=answer == STRONG and last,
            menu=menu is not None,
        ) as layout:
            if menu is None:
                return await interact(layout, name if first else None)
            return await interact_with_menu(layout, menu, name if first else None)

    # Only "Show all" leaves the menu with a value; a yes is `CONFIRMED`.
    return isinstance(await paged(fields, show), MenuResult)


async def _danger(
    name: str, title: str, page: "list[PageField]", first: bool
) -> "UiResult":
    with trezormodui.danger(title=title, fields=page) as layout:
        return await interact(layout, name if first else None)


def _menu(extras: "Sequence[Extra]", show_all: bool) -> "Menu[bool] | None":
    """The review's menu: its extras, "Show all" for details, and the way out.

    No ButtonRequest of its own: the review's step already sent one, and walking
    its menu is part of that same step.
    """
    if not extras and not show_all:
        return None
    leaves: list[MenuLeaf[bool]] = [_extra_leaf(extra) for extra in extras]
    if show_all:
        leaves.append(MenuLeaf(TR.buttons__show_all, _show_all))
    leaves.append(cancel_leaf(TR.buttons__cancel))
    return Menu(leaves)


async def _show_all() -> bool:
    return True


def _extra_leaf(extra: "Extra") -> "MenuLeaf[bool]":
    """One extra: its facts, page by page, then back to the review."""

    async def show(page: "list[PageField]", last: bool, first: bool) -> object:
        with trezormodui.extra(title=extra.label, fields=page) as layout:
            return await interact(layout, br_name=None, raise_on_cancel=None)

    async def _interact() -> None:
        await paged(extra.fields, show)

    return MenuLeaf(extra.label, _interact)


async def verify(
    screen: "Callable[..., LayoutObj[UiResult]]",
    name: str,
    confirmed: str,
    **kwargs: object,
) -> None:
    """Show a value of the person's own and wait until they confirm it matches.

    The screen sends its own ButtonRequest; the closing message sends none.
    """
    with screen(br_name=name, **kwargs) as layout:
        await raise_if_not_confirmed(layout, br_name=None)
    await done(None, confirmed)


async def done(name: str | None, text: str) -> None:
    """Say `text`, send a ButtonRequest called `name` if there is one, and go.

    Awaited, never spawned: a spawned layout starts with
    `workflow.close_others()`, which shuts down the task serving the app before
    it answers.
    """
    # A model's timeout screen goes away at once when animations are off, so
    # the screen would be gone before its ButtonRequest left; then it waits for
    # a tap instead, which is what a host driving the device does anyway.
    time_ms = 0 if utils.DISABLE_ANIMATION else _DONE_TIMEOUT_MS
    with trezormodui.done(text=text, time_ms=time_ms) as layout:
        await interact(layout, name, ButtonRequestType.Success)
