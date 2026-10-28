"""The screens that ask before the app acts: reviews, dangers and details."""

from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR
from trezor.ui.layouts.common import interact
from trezor.ui.layouts.menu import (
    Menu,
    MenuLeaf,
    cancel_leaf,
    interact_with_menu,
)
from trezor.wire import ActionCancelled
from trezor.wire.errors import DataError

from .fields import (
    ADDRESS,
    DATA,
    MAX_EXTRAS,
    Pager,
    details_items,
    has_warning,
    items,
    notes,
    values,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trezorui_api import UiResult

    from .fields import Field


async def review(
    name: str,
    title: str,
    facts: Sequence["Field"],
    extras: Sequence[tuple[str, Sequence["Field"]]],
    is_final: bool,
) -> "UiResult":
    """Ask the person to confirm the facts, with the extras in a menu.

    Returns the layout's decision, or raises `ActionCancelled` when it is refused.
    A final review is drawn with a hold on every model.

    A `data` fact is pulled one chunk at a time: each chunk is its own page, and
    the next one is pulled only after the person asks for it.

    A request the screens cannot draw — more than five extras, or more than one
    `data` fact — raises `DataError`, and the app is stopped.
    """
    if len(extras) > MAX_EXTRAS:
        raise DataError("more than 5 extras")
    if sum(1 for kind, _, _ in facts if kind == DATA) > 1:
        raise DataError("more than one data field")

    facts_with_values = values(facts)
    text = notes(facts) or None
    external_menu = bool(extras)
    base = len(facts)

    if len(facts_with_values) > 1 or has_warning(facts):
        pages = Pager(facts)
        while True:
            page = await pages.next()
            if page is None:
                raise DataError("No data chunks")
            chunked, last = page
            with trezorui_api.confirm_properties(
                title=title,
                items=items(chunked),
                hold=is_final and last,
                verb=_verb(last),
                external_menu=external_menu,
            ) as layout:
                result = await _with_extras(
                    layout, _page_name(name, pages), extras, base
                )
            if result is not trezorui_api.CONFIRMED or last:
                return result

    if not facts_with_values:
        with trezorui_api.confirm_action(
            title=title,
            action=text,
            description=None,
            hold=is_final,
            cancel=True,
            external_menu=external_menu,
        ) as layout:
            return await _with_extras(layout, name, extras, base)

    kind, _, value = facts_with_values[0]
    pages = Pager(facts)
    while True:
        page = await pages.next()
        if page is None:
            raise DataError("No data chunks")
        chunked, last = page
        if kind == DATA:
            value = values(chunked)[0][2]
        with trezorui_api.confirm_value(
            title=title,
            value=value,
            description=text,
            is_data=(kind == DATA),
            chunkify=(kind == ADDRESS),
            page_counter=(kind == DATA),
            hold=is_final and last,
            verb=_verb(last),
            cancel=True,
            external_menu=external_menu,
        ) as layout:
            result = await _with_extras(layout, _page_name(name, pages), extras, base)
        if result is not trezorui_api.CONFIRMED or last:
            return result


async def danger(
    name: str,
    title: str,
    facts: Sequence["Field"],
) -> "UiResult":
    """Ask the person to go on with something risky, the facts included.

    Returns the layout's decision, or raises `ActionCancelled` when it is refused.
    """
    pages = Pager(facts)
    while True:
        page = await pages.next()
        if page is None:
            raise DataError("No data chunks")
        chunked, last = page
        with trezorui_api.show_danger(
            title=title,
            description="",
            items=items(chunked),
        ) as layout:
            result = await interact(layout, _page_name(name, pages))
        if result is not trezorui_api.CONFIRMED or last:
            return result


async def details(
    name: str,
    title: str,
    facts: Sequence["Field"],
) -> bool:
    """Show the short version, and say whether the person wants the details.

    Returns `True` for the details, `False` for going on without them, or raises
    `ActionCancelled` when the screen is refused.
    """
    pages = Pager(facts)
    while True:
        page = await pages.next()
        if page is None:
            raise DataError("No data chunks")
        chunked, last = page
        with trezorui_api.confirm_with_info(
            title=title,
            items=details_items(chunked),
            verb=TR.buttons__confirm,
            verb_info=TR.buttons__show_all,
        ) as layout:
            result = await interact(
                layout, _page_name(name, pages), raise_on_cancel=None
            )
        if result is trezorui_api.INFO:
            return True
        if result is trezorui_api.CANCELLED:
            raise ActionCancelled
        if result is trezorui_api.CONFIRMED and last:
            return False
        if result is not trezorui_api.CONFIRMED:
            raise DataError("Unexpected layout result")


def _page_name(name: str, pages: "Pager") -> "str | None":
    """The step's name on its first page only: one ButtonRequest per step."""
    return name if pages.page == 1 else None


def _verb(last: bool) -> "str | None":
    """The right button's label: "Continue" until the last chunk, then the
    layout's own, which is "Confirm" or the hold."""
    return None if last else TR.buttons__continue


async def _with_extras(
    layout: "trezorui_api.LayoutObj[UiResult]",
    name: str | None,
    extras: Sequence[tuple[str, Sequence["Field"]]],
    base_index: int,
) -> "UiResult":
    """Run the review, offering its extras in a menu if it has any.

    The person can open the extras as often as they like and come back to the
    review; only the review's own decision is returned.
    """
    if not extras:
        return await interact(layout, name)
    return await interact_with_menu(layout, _extras_menu(extras, base_index), name)


def _extras_menu(
    extras: Sequence[tuple[str, Sequence["Field"]]],
    base_index: int,
) -> "Menu[None]":
    """The review's menu, one entry per extra.

    `base_index` is the flat index of the first extra's first fact: the request's
    own facts come first in the order core counts them.
    """
    leaves = []
    for label, extra_facts in extras:
        leaves.append(_extra_leaf(label, extra_facts, base_index))
        base_index += len(extra_facts)
    leaves.append(cancel_leaf(TR.buttons__cancel))
    return Menu(leaves)


def _extra_leaf(
    label: str,
    facts: Sequence["Field"],
    base_index: int,
) -> "MenuLeaf[None]":
    """One menu entry, showing that extra's facts and coming back to the review.

    No ButtonRequest of its own: the review's step already sent one, and walking
    its menu is part of that same step.
    """

    async def _interact() -> None:
        await _show_extra(label, facts, base_index)

    return MenuLeaf(label, _interact)


async def _show_extra(
    label: str,
    facts: Sequence["Field"],
    base_index: int,
) -> None:
    """Show an extra's facts, pulling its data one chunk at a time."""
    pages = Pager(facts, base_index)
    while True:
        page = await pages.next()
        if page is None:
            return
        chunked, last = page
        with trezorui_api.show_properties(
            title=label,
            value=items(chunked),
        ) as layout:
            result = await interact(layout, br_name=None, raise_on_cancel=None)
        if result is not trezorui_api.CONFIRMED or last:
            return
