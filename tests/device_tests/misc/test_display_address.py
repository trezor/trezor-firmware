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

"""DisplayAddress: the first consumer of WARD that is not WARD itself.

Everything in test_ward.py is the HOST driving WARD. This is an ON-DEVICE APP reading it:
the host names an address and nothing else, and the device decides what that address is
CALLED and how well it knows.

Four separable things are asserted here:
  - the host cannot name the label -- there is no field for it, and the screen's label
    tracks what WARD holds rather than anything the request said;
  - the source is chosen the way every other WARD read chooses it, up front on whether the
    session has synced, so an offline device emits no pull at all;
  - the screen SAYS which source it used, including when there was no label to find;
  - a failure to label is not a failure to display -- the address is shown regardless.

The WARD fixtures are imported from test_ward rather than rebuilt: an entry can only be
created by asking the device to build the leaf, and doing that correctly is exactly what
those helpers already encode.
"""

import pytest

from trezorlib import display_address, exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_trie import WardTrie
from .test_ward import _APP, _go_online, _pin, _Recorded, _seed

# `DisplayAddress` is registered behind the same `BITCOIN_ONLY` guard as WARD itself, so a
# BTC-only build has no handler for it and no such message type at all.
pytestmark = pytest.mark.ward

# A label the layouts render verbatim: lowercase, no spaces. `_Recorded.title` lowercases
# (titles are ours to spell, so case there is noise), and a value long enough to wrap gets a
# space inserted mid-token -- see `_Recorded.squashed`.
_ADDRESS = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
_LABEL = b"alice-savings"


def _show(
    session: Session,
    store: "WardTrie | None",
    *,
    app_id: str | None = _APP,
    address: str = _ADDRESS,
    online: bool = True,
) -> _Recorded:
    """Run one DisplayAddress, walking both of its screens, and return what they showed.

    The response sequence is pinned rather than left implicit: whether a pull happened is
    the whole of the difference between the two sources, and only the protocol shows it.
    An offline device must emit NO `WardEntryRequest`, which is asserted here by its absence
    from the expected responses -- and by the provider below, which fails loudly if asked.
    """
    rec = _Recorded()

    def refuse(_entry_key: bytes) -> ward.Answer:
        raise AssertionError("an offline lookup must not pull from the host")

    expected: list = [
        m.ButtonRequest(name="display_address_label"),
        m.ButtonRequest(name="display_address"),
        m.Success,
    ]
    if online:
        expected.insert(0, m.WardEntryRequest)

    with session.test_ctx as ctx:
        ctx.set_expected_responses(expected)
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        display_address.show_address(
            session,
            address,
            app_id=app_id,
            provider=ward.store_provider(store) if store is not None else refuse,
        )
    return rec


@pytest.mark.models("core")
@pytest.mark.ward_transport("connect")
def test_display_address_shows_the_label_wards_holds(session: Session):
    """The motivating case: an address the wallet has a name for is shown by that name."""
    store = WardTrie()
    # `_seed` leaves the session synced, which is what routes the read below to the host.
    _seed(session, store, _ADDRESS.encode(), _LABEL)

    rec = _show(session, store)

    assert _LABEL.decode() in rec.squashed + rec.title
    assert _ADDRESS in rec.squashed


@pytest.mark.models("core")
@pytest.mark.ward_transport("connect")
def test_display_address_says_so_when_there_is_no_label(session: Session):
    """An address with no entry is the ordinary case, and it is STATED.

    Absence that renders as a blank space cannot be read: a user who does not know a label
    would have appeared learns nothing from its not appearing. The address is still shown --
    an unlabelled address is not a suspect one.
    """
    store = WardTrie()
    _go_online(session, store)

    rec = _show(session, store)

    assert "no label" in (rec.text + rec.title).lower()
    assert _ADDRESS in rec.squashed


@pytest.mark.models("core")
@pytest.mark.ward_transport("connect")
def test_display_address_label_is_domain_separated(session: Session):
    """A label written by one app does not surface under another's domain.

    The entry_key is an HMAC over the domain, so asking under a different app_id lands on a
    different path -- which the host proves absent. Without this, any app could name any
    other app's addresses on the screen a user checks recipients against.
    """
    store = WardTrie()
    _seed(session, store, _ADDRESS.encode(), _LABEL)

    rec = _show(session, store, app_id="OTHER")

    assert _LABEL.decode() not in rec.squashed + rec.title
    assert "no label" in (rec.text + rec.title).lower()


@pytest.mark.models("core")
@pytest.mark.ward_transport("connect")
def test_display_address_offline_serves_the_kept_label(session: Session):
    """A host that never syncs is still served -- from the device's own store, and said so.

    This is the state a WARD-unaware host leaves the device in. The pull is not attempted at
    all: the provider above raises if it is, and `WardEntryRequest` is absent from the
    expected responses.
    """
    store = WardTrie()
    _seed(session, store, _ADDRESS.encode(), _LABEL)
    _pin(session, store, _ADDRESS.encode(), "ward_pin_cached_entry")

    fresh = session.test_ctx.get_session()
    rec = _show(fresh, None, online=False)

    assert _LABEL.decode() in rec.squashed + rec.title
    assert "offline" in (rec.text + rec.title).lower()


@pytest.mark.models("core")
@pytest.mark.ward_transport("connect")
def test_display_address_offline_without_a_kept_label_still_shows_the_address(
    session: Session,
):
    """The failure that must not become an address failure.

    Nothing kept, nothing to pull: there is no label to show and no way to get one. The
    address is shown anyway, because the lookup failing says nothing about it.
    """
    store = WardTrie()
    _seed(session, store, _ADDRESS.encode(), _LABEL)  # written, but never pinned

    fresh = session.test_ctx.get_session()
    rec = _show(fresh, None, online=False)

    assert _ADDRESS in rec.squashed
    assert "no label kept" in (rec.text + rec.title).lower()


@pytest.mark.models("core")
def test_display_address_rejects_an_empty_address(session: Session):
    """The one refusal. A screen showing an empty string is worse than an error."""
    with pytest.raises(exceptions.TrezorFailure, match="address"):
        display_address.show_address(session, "")


def test_display_address_has_no_field_for_a_label():
    """The host cannot name the recipient on the screen the recipient is checked against.

    Asserted against the message DEFINITION, not a behaviour: this is a property of the
    protocol, and it stops holding the moment someone adds a convenience field for it. No
    device needed.
    """
    fields = {f.name for f in m.DisplayAddress.FIELDS.values()}
    assert fields == {
        "address",
        "title",
        "subtitle",
        "case_sensitive",
        "chunkify",
        "app_id",
    }
