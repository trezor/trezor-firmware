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
from trezormodui import DANGER, DETAILS, STRONG, TEXT_SOURCE

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence
    from typing import TypeVar

    from trezormodui import Field as PageField
    from trezorui_api import LayoutObj, UiResult

    from . import Extra

    T = TypeVar("T")

    # A fact: `(kind, label, value)`, the label `None` for notes and warnings.
    # A `text_source` field's value is a source read while the person pages.
    Field = tuple[int, str | None, "str | Source"]

# How long the closing screen stays up before it goes away.
_DONE_TIMEOUT_MS = const(3200)


class Source:
    """The text of a `text_source` field, read while the person pages.

    `read(offset, length)` returns its UTF-8 bytes. The pager reads in order,
    from the start, each range once, so a source may hash what it hands out:
    the text on the screen is then the text that gets signed.
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

    A review needs at least one fact. Every entry of the menu counts against
    its size: each offered extra, the way out, and "Show all" of a details
    answer. An extra with no facts is not offered. A review's facts hold at
    most `MAX_STREAMED_FIELDS` streamed fields, and an extra none: it can be
    opened again, and what it streams would be read again. Anything else raises
    `ValueError`.
    """
    if not fields:
        raise ValueError("a review needs a fact")
    offered = [extra for extra in extras if extra.fields]
    if len(offered) > trezormodui.max_extras(answer):
        raise ValueError("more extras than the menu has room for")
    if _streamed(fields) > trezormodui.MAX_STREAMED_FIELDS:
        raise ValueError("too many streamed fields")
    if any(_streamed(extra.fields) for extra in offered):
        raise ValueError("a streamed field cannot be in an extra")
    return offered


def _streamed(facts: "Sequence[Field]") -> int:
    """How many of `facts` are streamed: today, the text sources."""
    return sum(kind == TEXT_SOURCE for kind, _, _ in facts)


class Pager:
    """The pages of a list of facts: one fact per page, a `text_source` field
    one chunk per page.

    A chunk is read only when its page is drawn, so a refusal between pages
    reads nothing more. A chunk may end inside a character: its first bytes are
    kept and shown with the next chunk.
    """

    def __init__(self, fields: "Sequence[Field]") -> None:
        self.fields = fields
        self.index = 0
        self.offset = 0
        self.carry = b""

    async def next(self) -> "tuple[list[PageField], bool]":
        """The next page, and whether it is the last."""
        kind, label, value = self.fields[self.index]
        if kind != TEXT_SOURCE:
            assert isinstance(value, str)
            self.index += 1
            return [(kind, label, value)], self.index >= len(self.fields)
        assert isinstance(value, Source)
        offset = self.offset
        length = min(trezormodui.TEXT_CHUNK_BYTES, value.total - offset)
        chunk = self.carry + (await value.read(offset, length) if length else b"")
        self.offset = offset + length
        end = self.offset >= value.total
        text, self.carry = _decode(chunk, end)
        if end:
            self.index += 1
            self.offset = 0
        return [(kind, label, text)], self.index >= len(self.fields)


def _decode(chunk: bytes, end: bool) -> "tuple[str, bytes]":
    """The text of `chunk`, and the bytes of a character it cuts off at its end.

    A UTF-8 character is at most four bytes, so at most three can be cut off.
    At the end of the text nothing may be left over. Anything that is not
    UTF-8 raises `ValueError`.
    """
    if end:
        return chunk.decode(), b""
    for cut in range(4):
        try:
            return chunk[: len(chunk) - cut].decode(), chunk[len(chunk) - cut :]
        except UnicodeError:
            pass
    raise ValueError("text source is not UTF-8")


async def paged(
    fields: "Sequence[Field]",
    show: "Callable[[list[PageField], bool], Awaitable[T]]",
) -> "T":
    """Show the pages of `fields` until one is not confirmed, or the last is.

    `show(page, last)` draws one page and returns its result.
    """
    pager = Pager(fields)
    while True:
        page, last = await pager.next()
        result = await show(page, last)
        if result is not trezorui_api.CONFIRMED or last:
            return result


async def review(
    name: str,
    title: str,
    fields: "Sequence[Field]",
    extras: "Sequence[Extra]",
    answer: int,
) -> bool:
    """Show a review and wait for its answer.

    Returns `True` when the person picked "Show all" of a details answer, and
    `False` for a yes. A refusal raises `ActionCancelled`. Any other result is
    not an answer the review asked for, and raises `RuntimeError`: nothing but
    a yes counts as one.
    """
    offered = check(fields, extras, answer)
    if answer == DANGER:
        result = await paged(fields, lambda page, last: _danger(name, title, page))
        if result is not trezorui_api.CONFIRMED:
            raise RuntimeError  # unexpected result
        return False

    menu = _menu(offered, answer == DETAILS)

    async def show(page: "list[PageField]", last: bool) -> object:
        # Every page sends the step's ButtonRequest: each is a screen the
        # person can act on, and the host may need to know.
        with trezormodui.review(
            title=title,
            fields=page,
            verb=None if last else TR.buttons__continue,
            hold=answer == STRONG and last,
            menu=menu is not None,
        ) as layout:
            if menu is None:
                return await interact(layout, name)
            return await interact_with_menu(layout, menu, name)

    result = await paged(fields, show)
    if result is trezorui_api.CONFIRMED:
        return False
    # Only "Show all" leaves the menu with a value.
    if answer == DETAILS and isinstance(result, MenuResult) and result.value is True:
        return True
    raise RuntimeError  # unexpected result


async def _danger(name: str, title: str, page: "list[PageField]") -> "UiResult":
    with trezormodui.danger(title=title, fields=page) as layout:
        return await interact(layout, name)


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

    async def show(page: "list[PageField]", last: bool) -> object:
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
