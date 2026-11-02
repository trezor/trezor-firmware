# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""The modui layouts the testapp exposes, and how the tests read and answer
them on the device.

The requests and their facts are built with the host library, `testapp_host`;
its `messages` is the one message module of the modui tests, so a request and
the facts nested in it are always classes of the same module.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from trezorlib.debuglink import LayoutType

# The host library lives beside the tests rather than in their environment.
HOST = str(Path(__file__).resolve().parents[1] / "host")
if HOST not in sys.path:
    sys.path.insert(0, HOST)

from testapp_host import (  # noqa: E402
    SHOWCASES,
    TestApp,
    address,
    amount,
    data,
    extras,
    note,
    showcases,
    text,
    warning,
)
from testapp_host import messages as m  # noqa: E402

from . import testapp_ext  # noqa: E402

if TYPE_CHECKING:
    from trezorlib import protobuf
    from trezorlib.client import Session
    from trezorlib.debuglink import DebugLink, LayoutContent

# Passed on from the host library, so the tests take everything modui from here.
__all__ = [
    "SHOWCASES",
    "TestApp",
    "address",
    "amount",
    "data",
    "extras",
    "m",
    "note",
    "showcases",
    "text",
    "warning",
]

APP_NAME = "testapp.trezor.io"

XPUB = (
    "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkk"
    "fHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U"
)

# An extra as a test reads it: its label, and each fact's label and value as
# the screen shows them.
ShownExtra = tuple[str, tuple[tuple[str, str], ...]]


# ============================================================================
# Requests
# ============================================================================


def show(
    session: "Session", instance_id: int, request: "protobuf.MessageType"
) -> m.Reply:
    """Show one layout and return how it ended."""
    result = testapp_ext.call_ext(
        session, instance_id, msg_data=request, expect=[m.UiResult]
    )
    return m.Reply(result.reply)


def tick(session: "Session", instance_id: int, request: "protobuf.MessageType") -> None:
    """Send one request of a running progress; the app answers by asking for the
    next one."""
    testapp_ext.call_ext(
        session, instance_id, msg_data=request, expect=[m.ProgressTick]
    )


@contextmanager
def progress(
    session: "Session", instance_id: int, label: str, total: int | None
) -> Iterator[Callable[[int | str], None]]:
    """Run a progress for as long as the `with` block runs, then end it.

    The block reports the work with the function it is handed: an int is that
    many units of work done, a str changes the label under the bar. A progress
    asks nothing, so it ends answering `Confirmed`.
    """
    tick(session, instance_id, m.ShowProgress(label=label, total=total))

    def report(step: int | str) -> None:
        if isinstance(step, str):
            tick(session, instance_id, m.ProgressLabel(label=step))
        else:
            tick(session, instance_id, m.ProgressStep(units=step))

    yield report
    assert show(session, instance_id, m.ProgressEnd()) is m.Reply.Confirmed


def text_extras(items: Iterable[ShownExtra]) -> list[m.Extra]:
    """Extras of text facts, which the screen shows as written."""
    return extras(*[(label, [text(*fact) for fact in facts]) for label, facts in items])


# ============================================================================
# Reading the screen
# ============================================================================


def br_name(step: str) -> str:
    """The name a host sees for one step of the app."""
    return f"{APP_NAME}/{step}"


def flat(value: str) -> str:
    """Text with every whitespace removed, for comparing values the model
    wraps across lines or pages."""
    return "".join(value.split())


def screen_text(layout: "LayoutContent") -> str:
    """Everything a screen says, the footer included.

    Eckhart keeps a closing screen's description in the content, Delizia in the
    footer, so a description is looked for wherever the model put it.
    """
    return flat(" ".join([layout.title(), layout.text_content(), layout.footer()]))


def page(debug: "DebugLink") -> None:
    """Turn one page of a paged layout: Eckhart's action bar, Delizia's swipe."""
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
    else:
        debug.click(debug.screen_buttons.ok())


def read_all_pages(debug: "DebugLink", pages: int | None = None) -> list[str]:
    """Read every page of a paged layout, leaving the last one up.

    `pages` is the count the ButtonRequest reported, for a layout whose own
    trace has none: Delizia's review traces no page count of its own.
    """
    layout = debug.read_layout()
    if pages is None:
        pages = layout.page_count()
    texts = [layout.text_content()]
    for _ in range(pages - 1):
        page(debug)
        texts.append(debug.read_layout().text_content())
    return texts


# ============================================================================
# Answering
# ============================================================================


def confirm(debug: "DebugLink") -> None:
    """Confirm the last page of a non-final layout by the model's own gesture."""
    page(debug)


def confirm_hold(debug: "DebugLink") -> None:
    """Confirm the last page of a final layout, which every model draws with a
    hold."""
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.synchronize_at("PromptScreen")
        debug.click(debug.screen_buttons.tap_to_confirm(), hold_ms=2200)
    else:
        debug.click(debug.screen_buttons.ok(), hold_ms=1500)


def open_menu(debug: "DebugLink") -> None:
    """Open the layout's own menu, a danger's or a verify flow's, and wait for
    it to be drawn."""
    debug.click(debug.screen_buttons.menu())
    debug.synchronize_at("VerticalMenu")


def open_extras_menu(debug: "DebugLink") -> None:
    """Open a review's menu - its extras, "Show all" of a details answer, and
    the way out - and wait for it to be drawn."""
    debug.press_info()
    debug.synchronize_at("VerticalMenu")


def open_extra(debug: "DebugLink", items: Sequence[ShownExtra], index: int) -> None:
    """Open the extra at `index` of a review's menu, check what it shows, and come
    back to the review."""
    open_extras_menu(debug)
    debug.button_actions.navigate_to_menu_item(index)
    label, facts = items[index]
    extra = debug.read_layout()
    assert label in extra.title()
    shown = flat(extra.text_content())
    for _, value in facts:
        assert flat(value) in shown
    debug.click(debug.screen_buttons.menu())  # close the extra
    debug.click(debug.screen_buttons.menu())  # close the menu


def show_all(debug: "DebugLink", offered: int = 0) -> None:
    """Pick "Show all" of a details answer: the menu entry after the `offered`
    extras."""
    open_extras_menu(debug)
    debug.button_actions.navigate_to_menu_item(offered)


def go_on_past_danger(debug: "DebugLink") -> None:
    """Take a danger's detour: its menu's way forward."""
    open_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)


def open_account_info(
    debug: "DebugLink",
    present: tuple[str, ...] = (),
    absent: tuple[str, ...] = (),
) -> None:
    """Open the account info of a verify flow, check it, and come back."""
    open_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)
    shown = flat(debug.read_layout().text_content())
    for value in present:
        assert flat(value) in shown
    for value in absent:
        assert flat(value) not in shown
    debug.click(debug.screen_buttons.menu())  # close the account info
    debug.click(debug.screen_buttons.menu())  # close the menu


def confirm_verify(debug: "DebugLink", pages: int) -> None:
    """Page to the end of a verify flow, confirm, dismiss its success screen, and
    check it said so."""
    if debug.layout_type is LayoutType.Delizia:
        # Delizia pages the value, then asks for the tap on a prompt screen.
        for _ in range(pages - 1):
            debug.swipe_up()
        debug.synchronize_at("PromptScreen")
        debug.click(debug.screen_buttons.tap_to_confirm())
    else:
        for _ in range(pages - 1):
            debug.click(debug.screen_buttons.ok())
        debug.click(debug.screen_buttons.ok())
    success = debug.read_layout(wait=True)
    assert "confirmed" in screen_text(success).lower()
    debug.press_yes()


# ============================================================================
# Backing out
# ============================================================================


def cancel_by_menu(debug: "DebugLink", entries: int) -> None:
    """Back out of a review by the way out at the end of its menu, after its
    other `entries`: the extras, and "Show all" of a details answer."""
    open_extras_menu(debug)
    debug.button_actions.navigate_to_menu_item(entries)


def cancel_danger(debug: "DebugLink") -> None:
    """Back out of a danger by its menu, and dismiss the closing screen."""
    open_menu(debug)
    debug.button_actions.navigate_to_menu_item(0)
    debug.press_yes()


def cancel_verify(debug: "DebugLink") -> None:
    """Back out of a verify flow by the person's "does not match" path."""
    open_menu(debug)
    debug.button_actions.navigate_to_menu_item(2)
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.click(debug.screen_buttons.tap_to_confirm())
    else:
        debug.click(debug.screen_buttons.ok())
