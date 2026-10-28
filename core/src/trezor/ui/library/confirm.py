"""The screens that ask before the app acts: reviews, dangers and details."""

from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR
from trezor.ui.layouts.common import interact
from trezor.ui.layouts.menu import (
    Menu,
    cancel_leaf,
    interact_with_menu,
    leaf_from_layout,
)
from trezor.wire import ActionCancelled
from trezor.wire.errors import DataError

from .fields import (
    ADDRESS,
    DATA,
    details_items,
    has_warning,
    items,
    notes,
    values,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trezor.ui.layouts.menu import MenuLeaf
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
    """
    facts_with_values = values(facts)
    text = notes(facts) or None
    external_menu = bool(extras)

    if len(facts_with_values) > 1 or has_warning(facts):
        with trezorui_api.confirm_properties(
            title=title,
            items=items(facts),
            hold=is_final,
            external_menu=external_menu,
        ) as layout:
            return await _with_extras(layout, name, extras)

    if not facts_with_values:
        with trezorui_api.confirm_action(
            title=title,
            action=text,
            description=None,
            hold=is_final,
            cancel=True,
            external_menu=external_menu,
        ) as layout:
            return await _with_extras(layout, name, extras)

    kind, _, value = facts_with_values[0]
    with trezorui_api.confirm_value(
        title=title,
        value=value,
        description=text,
        is_data=(kind == DATA),
        chunkify=(kind == ADDRESS),
        page_counter=(kind == DATA),
        hold=is_final,
        cancel=True,
        external_menu=external_menu,
    ) as layout:
        return await _with_extras(layout, name, extras)


async def danger(
    name: str,
    title: str,
    facts: Sequence["Field"],
) -> "UiResult":
    """Ask the person to go on with something risky, the facts included.

    Returns the layout's decision, or raises `ActionCancelled` when it is refused.
    """
    with trezorui_api.show_danger(
        title=title,
        description="",
        items=items(facts),
    ) as layout:
        return await interact(layout, name)


async def details(
    name: str,
    title: str,
    facts: Sequence["Field"],
) -> bool:
    """Show the short version, and say whether the person wants the details.

    Returns `True` for the details, `False` for going on without them, or raises
    `ActionCancelled` when the screen is refused.
    """
    with trezorui_api.confirm_with_info(
        title=title,
        items=details_items(facts),
        verb=TR.buttons__confirm,
        verb_info=TR.buttons__show_all,
    ) as layout:
        result = await interact(layout, name, raise_on_cancel=None)

    if result is trezorui_api.INFO:
        return True
    if result is trezorui_api.CONFIRMED:
        return False
    if result is trezorui_api.CANCELLED:
        raise ActionCancelled
    raise DataError("Unexpected layout result")


async def _with_extras(
    layout: "trezorui_api.LayoutObj[UiResult]",
    name: str,
    extras: Sequence[tuple[str, Sequence["Field"]]],
) -> "UiResult":
    """Run the review, offering its extras in a menu if it has any.

    The person can open the extras as often as they like and come back to the
    review; only the review's own decision is returned.
    """
    if not extras:
        return await interact(layout, name)
    menu = Menu(
        [_extra_leaf(label, extra_facts) for label, extra_facts in extras]
        + [cancel_leaf(TR.buttons__cancel)]
    )
    return await interact_with_menu(layout, menu, name)


def _extra_leaf(
    label: str,
    facts: Sequence["Field"],
) -> "MenuLeaf[None]":
    """One menu entry, showing that extra's facts and coming back to the review."""
    # No ButtonRequest of its own: the review's step already sent one, and
    # walking its menu is part of that same step.
    return leaf_from_layout(
        label,
        lambda: trezorui_api.show_properties(title=label, value=items(facts)),
    )
