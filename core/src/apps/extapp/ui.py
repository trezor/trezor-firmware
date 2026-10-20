from micropython import const
from typing import TYPE_CHECKING

import trezorui_api
from trezor import TR
from trezor.ui.layouts.menu import (
    Menu,
    cancel_leaf,
    interact_with_menu,
    leaf_from_layout,
)
from trezor.wire import ActionCancelled
from trezor.wire.errors import DataError

from .session import SERVICE_UI

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import Any

    from trezor.ui.layouts.menu import MenuLeaf
    from trezorui_api import LayoutContext

    from .session import Session

# Kinds of an app's UI request, decoded by `trezorui_api.deserialize_ui_message`.
_KIND_ACTION = const(0)
_KIND_VALUE = const(1)
_KIND_DATA = const(2)
_KIND_SUMMARY = const(3)
_KIND_PROPERTIES = const(4)
_KIND_NOTICE = const(5)


async def handle(session: Session, msg: IpcMessage) -> None:
    """Show the layout the app asked for and send the app the person's answer."""
    try:
        result = await _show_layout(bytes(msg.data))
    except ActionCancelled:
        result = trezorui_api.CANCELLED
    except Exception as e:
        # The request cannot be drawn. Answering would leave the app waiting on
        # a screen that never existed, so the app stops.
        session.die(DataError(f"Cannot show the app's screen: {e}"))
    if __debug__:
        log.debug(__name__, f"UI interaction result: {result}")

    try:
        # Only a decision is an answer. Anything else a layout ends with is a
        # bug, never a yes, and the app stops.
        answer = trezorui_api.encode_ui_result(result=result)
    except Exception as e:
        session.die(DataError(f"Unexpected layout result: {e}"))
    try:
        session.send(SERVICE_UI, 0, answer)
    except Exception as e:
        session.die(DataError(f"Cannot send the screen's answer: {e}"))


async def _show_layout(data: bytes) -> Any:
    """Show one layout of an app, with its extras menu if it has one, and
    return the layout's result.

    The request carries the layout's extras, so the menu is walked here: the
    person can open the menu, look at extras and come back as often as they
    like, and only the decision reaches the caller. Raises `ActionCancelled`
    when the layout is refused, by whatever way out the model offers.
    """
    kind, br_name, *fields, extras = trezorui_api.deserialize_ui_message(data=data)
    menu = Menu(
        [_properties_leaf(label, props) for label, props in extras]
        + [cancel_leaf(TR.buttons__cancel)]
    )
    with _BLOCKS[kind](*fields, extras) as layout:
        return await interact_with_menu(layout, menu, br_name)


def _properties_leaf(label: str, props: list) -> "MenuLeaf[None]":
    """A menu entry showing one extra's key/value facts."""
    return leaf_from_layout(
        label,
        lambda: trezorui_api.show_properties(title=label, value=props),
    )


def _ctx_action(
    title: str,
    action: str,
    description: str | None,
    subtitle: str | None,
    hold: bool,
    extras: list,
) -> "LayoutContext[Any]":
    """`confirm::action` — a question about an action."""
    return trezorui_api.confirm_action(
        title=title,
        action=action,
        description=description,
        subtitle=subtitle,
        hold=hold,
        # Every confirmation can be refused; how is the model's.
        cancel=True,
        external_menu=bool(extras),
    )


def _ctx_value(
    title: str,
    value: str,
    description: str | None,
    subtitle: str | None,
    chunkify: bool,
    footer: tuple[str, bool] | None,
    hold: bool,
    extras: list,
) -> "LayoutContext[Any]":
    """`confirm::value` — one value, such as an address or an amount."""
    return trezorui_api.confirm_value(
        title=title,
        value=value,
        description=description,
        subtitle=subtitle,
        chunkify=chunkify,
        footer=footer,
        hold=hold,
        # Every confirmation can be refused; how is the model's.
        cancel=True,
        external_menu=bool(extras),
    )


def _ctx_data(
    title: str,
    data: bytes,
    subtitle: str | None,
    extras: list,
) -> "LayoutContext[Any]":
    """`confirm::data` — raw bytes, as hex, a page at a time."""
    return trezorui_api.confirm_value(
        title=title,
        value=data,
        description=None,
        subtitle=subtitle,
        page_counter=True,
        # Every confirmation can be refused; how is the model's.
        cancel=True,
        external_menu=bool(extras),
    )


def _ctx_summary(
    title: str,
    amount: str | None,
    amount_label: str | None,
    fee: str | None,
    fee_label: str | None,
    extras: list,
) -> "LayoutContext[Any]":
    """`confirm::summary` — the closing amount and fee of a transaction."""
    return trezorui_api.confirm_summary(
        amount=amount,
        amount_label=amount_label,
        # WIP: no model can leave the fee out; an empty one stands in for it.
        fee=fee or "",
        fee_label=fee_label or "",
        title=title,
        external_menu=bool(extras),
    )


def _ctx_properties(
    title: str,
    subtitle: str | None,
    props: list,
    hold: bool,
    extras: list,
) -> "LayoutContext[Any]":
    """`confirm::properties` — a list of key/value facts."""
    return trezorui_api.confirm_properties(
        title=title,
        subtitle=subtitle,
        items=props,
        hold=hold,
        external_menu=bool(extras),
    )


def _ctx_notice(
    severity: int,
    title: str,
    content: str,
    cancel: bool,
    extras: list,
) -> "LayoutContext[Any]":
    """`notice::show` — a notice of some severity."""
    return trezorui_api.show_notice(
        severity=severity,
        title=title,
        content=content,
        cancel=cancel,
        external_menu=bool(extras),
    )


# One builder per kind; each takes the layout's decoded fields and its extras.
_BLOCKS = {
    _KIND_ACTION: _ctx_action,
    _KIND_VALUE: _ctx_value,
    _KIND_DATA: _ctx_data,
    _KIND_SUMMARY: _ctx_summary,
    _KIND_PROPERTIES: _ctx_properties,
    _KIND_NOTICE: _ctx_notice,
}
