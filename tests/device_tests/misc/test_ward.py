# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

"""WARD phase 1: plaintext, PULL-only.

The device holds nothing. It asks the host for the entry mid-workflow and displays it.
These tests assert the pull actually happens (the host is asked for exactly what the
caller named) and that the screen labels the value as unverified -- which it is, since
nothing in this phase authenticates it.
"""

from typing import Callable

import pytest

from trezorlib import exceptions, ward
from trezorlib import messages as m
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent

from ...input_flows import InputFlowConfirmAllWarnings

_APP = "TEST"


def _page_collector() -> "tuple[Callable[[LayoutContent], None], Callable[[], str]]":
    """Collect the text of every page of a confirm screen.

    Paging is delegated to `InputFlowConfirmAllWarnings`, which knows how each layout
    advances -- notably T3W1 clicks OK while the others swipe up (see
    `DebugUI._paginate_and_confirm`). Hand-rolling `swipe_up()` here silently read page
    one twice on T3W1, so anything below the fold went unasserted.
    """
    pages: list[str] = []

    def on_page(layout: LayoutContent) -> None:
        pages.append(layout.text_content())

    def content() -> str:
        return "\n".join(pages)

    return on_page, content


# The full PULL round: the device asks for the entry, we answer, then it shows it.
# Pinning the sequence is what proves the pull happened at the protocol level; the
# screen assertions below only prove what was rendered.
_PULL_RESPONSES = [
    m.WARDEntryRequest,
    m.ButtonRequest(name="ward_get_entry"),
    m.Success,
]


@pytest.mark.models("core")
def test_ward_get_entry_pulls_and_shows(session: Session):
    """The device pulls the value from the host and renders it."""
    asked: list[tuple[str, bytes]] = []

    def provider(app_id: str, identifier: bytes):
        asked.append((app_id, identifier))
        return b"Petr_label"

    on_page, content = _page_collector()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_PULL_RESPONSES)
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=on_page).get())
        res = ward.get_entry(session, _APP, b"addr1", provider)

    # the device asked the host for exactly what we named -- i.e. it really pulled
    assert asked == [(_APP, b"addr1")]
    assert res.message == "WARD entry shown"

    # the pulled value reached the screen, and it is marked unverified
    assert "Petr_label" in content()
    assert "not verified" in content().lower()


@pytest.mark.models("core")
def test_ward_get_entry_absent_is_distinct_from_empty(session: Session):
    """A missing entry (provider returns None) must not look like an entry whose value
    happens to be empty: the device says it was not found."""
    on_page, content = _page_collector()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_PULL_RESPONSES)
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=on_page).get())
        ward.get_entry(session, _APP, b"nope", lambda _a, _i: None)

    assert "no entry" in content().lower()


@pytest.mark.models("core")
def test_ward_get_entry_empty_value_is_shown_as_an_entry(session: Session):
    """The converse of the above: a present-but-empty value IS an entry, so the screen
    must not claim it was not found."""
    on_page, content = _page_collector()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_PULL_RESPONSES)
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=on_page).get())
        ward.get_entry(session, _APP, b"empty", lambda _a, _i: b"")

    assert "no entry" not in content().lower()
    assert "not verified" in content().lower()


@pytest.mark.models("core")
def test_ward_get_entry_uses_the_dict_provider(session: Session):
    """The dict-backed provider stands in for the host DB in this phase."""
    entries = {(_APP, b"addr1"): b"one", (_APP, b"addr2"): b"two"}

    on_page, content = _page_collector()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_PULL_RESPONSES)
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=on_page).get())
        ward.get_entry(session, _APP, b"addr2", ward.dict_provider(entries))

    assert "two" in content()


@pytest.mark.models("core")
def test_ward_get_entry_rejects_empty_identifier(session: Session):
    """The handler validates its inputs instead of pulling for a null key.

    The wire fields are `optional` on purpose -- a proto2 `required` field a caller
    forgets to set is an encode-time failure in every binding, which has bitten this
    protocol before -- so the check has to live in the handler. It fails before any
    screen, hence no input flow.
    """
    with pytest.raises(exceptions.TrezorFailure, match="required"):
        ward.get_entry(session, _APP, b"", lambda _a, _i: b"x")
