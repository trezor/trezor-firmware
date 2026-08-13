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

"""WARD phase 1: plaintext, PULL-only, keyed path.

The device holds nothing. It derives an opaque 32-byte `entry_key` from a seed the host
does not have, asks the host for THAT, and displays what comes back. The host's store is
keyed by the opaque key and contains no identifiers at all.

These tests assert three separate things, which is worth keeping distinct:
  - the pull happens, and names only the opaque key (protocol);
  - the key is the RIGHT one, i.e. the actual HMAC of the scope (crypto, via the
    test-only oracle in `tests/ward_keys.py`);
  - the screen shows the value and labels it unverified, which it is -- nothing in this
    phase authenticates it (UI).
"""

import pytest

from trezorlib import exceptions, ward
from trezorlib import messages as m
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_keys import bip39_seed, derive_k_path
from ...ward_keys import entry_key as expected_entry_key

_APP = "TEST"

# The device under test is set up with the default mnemonic and no passphrase
# (`SetupParams` in tests/conftest.py), so the oracle can reproduce its K_path.
_K_PATH = derive_k_path(bip39_seed(" ".join(["all"] * 12)))


class _Recorded:
    """Everything a confirm screen showed, accumulated page by page.

    Title and body are kept APART because `text_content()` does not include the title --
    asserting a title against the body silently never matches, and worse, a loose
    substring can match the body by accident (`"add"` is inside `"addr1"`, which made an
    add/update assertion pass for any title at all). Titles are matched as whole phrases
    against `title`, values against `text`.

    Paging is delegated to `InputFlowConfirmAllWarnings`, which knows how each layout
    advances -- notably T3W1 clicks OK while the others swipe up (see
    `DebugUI._paginate_and_confirm`). Hand-rolling `swipe_up()` here read page one twice
    on T3W1, so anything below the fold went unasserted.
    """

    def __init__(self) -> None:
        self._titles: list[str] = []
        self._texts: list[str] = []

    def on_page(self, layout: LayoutContent) -> None:
        self._titles.append(layout.title())
        self._texts.append(layout.text_content())

    @property
    def title(self) -> str:
        """Every page's title, lowercased -- titles are ours to spell, so case is noise."""
        return "\n".join(self._titles).lower()

    @property
    def text(self) -> str:
        """Every page's body, case preserved -- values under test are case-sensitive."""
        return "\n".join(self._texts)


def _expected(br_name: str) -> list:
    """The full PULL round: the device asks for the entry, we answer, then it confirms.

    Pinning the sequence is what proves the pull happened at the protocol level; the
    screen assertions only prove what was rendered. Every request in this phase has the
    same shape, differing only in the screen it ends on.
    """
    return [m.WARDEntryRequest, m.ButtonRequest(name=br_name), m.Success]


def _recording_provider(store: dict[bytes, bytes], asked: list[bytes]):
    """A dict-backed provider that also records the keys it was asked for."""

    def provider(entry_key: bytes):
        asked.append(entry_key)
        return store.get(entry_key)

    return provider


# --- the keyed path --------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_pull_names_only_the_opaque_key(session: Session):
    """The request must carry a 32-byte key and NOTHING that reveals the entry.

    This is the property the whole step exists for, so it is asserted directly on the
    bytes rather than inferred: neither the domain nor the identifier may appear anywhere
    in what the host receives.
    """
    identifier = b"addr1"
    asked: list[bytes] = []

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.get_entry(session, _APP, identifier, _recording_provider({}, asked))

    assert len(asked) == 1
    key = asked[0]
    assert len(key) == 32
    assert identifier not in key
    assert _APP.encode() not in key


@pytest.mark.models("core")
def test_ward_pull_key_is_the_expected_hmac(session: Session):
    """The key is not merely opaque, it is the RIGHT 32 bytes.

    Computed independently from the device's known test seed -- see the warning in
    tests/ward_keys.py about why only a test may do this. A device that derived from the
    wrong SLIP-21 label, or built the scope differently, would still pass every other
    test in this file while putting every entry at the wrong path.
    """
    identifier = b"addr1"
    asked: list[bytes] = []

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.get_entry(session, _APP, identifier, _recording_provider({}, asked))

    assert asked == [expected_entry_key(_K_PATH, _APP, identifier)]


@pytest.mark.models("core")
def test_ward_pull_key_is_deterministic_and_domain_separated(session: Session):
    """Same (app_id, identifier) -> same key; different app_id -> different key.

    Determinism is what makes the store usable at all; domain separation is what stops
    one app's entry from resolving another's. Both are observable from the host side
    without any knowledge of the seed.
    """
    identifier = b"addr1"
    asked: list[bytes] = []
    provider = _recording_provider({}, asked)

    for app_id in (_APP, _APP, "OTHER"):
        rec = _Recorded()
        with session.test_ctx as ctx:
            ctx.set_expected_responses(_expected("ward_get_entry"))
            ctx.set_input_flow(
                InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
            )
            ward.get_entry(session, app_id, identifier, provider)

    first, again, other = asked
    assert first == again
    assert first != other


@pytest.mark.models("core")
def test_ward_rejects_nul_in_app_id(session: Session):
    """The scope's 0x00 delimiters are only unambiguous while the fields exclude 0x00.

    Otherwise the same preimage re-splits into a different tuple and two distinct
    entries collide on one key. app_id arrives as a protobuf string and 0x00 is valid
    UTF-8, so this is reachable input. Fails before any pull or screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="NUL"):
        ward.get_entry(session, "bad\x00app", b"addr1", lambda _k: b"x")


# --- read -------------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_get_entry_pulls_and_shows(session: Session):
    """The device pulls the value from the host and renders it."""
    asked: list[bytes] = []
    key = expected_entry_key(_K_PATH, _APP, b"addr1")

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = ward.get_entry(
            session, _APP, b"addr1", _recording_provider({key: b"Petr_label"}, asked)
        )

    # the device asked the host for exactly the key we expected -- i.e. it really pulled
    assert asked == [key]
    assert res.entry_key == key
    assert res.success.message == "WARD entry shown"

    # the pulled value reached the screen, and it is marked unverified
    assert "unverified entry" in rec.title
    assert "Petr_label" in rec.text
    assert "not verified" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_absent_is_distinct_from_empty(session: Session):
    """A missing entry (provider returns None) must not look like an entry whose value
    happens to be empty: the device says it was not found."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.get_entry(session, _APP, b"nope", lambda _k: None)

    assert "entry not found" in rec.title
    assert "no entry" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_empty_value_is_shown_as_an_entry(session: Session):
    """The converse of the above: a present-but-empty value IS an entry, so the screen
    must not claim it was not found."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.get_entry(session, _APP, b"empty", lambda _k: b"")

    assert "unverified entry" in rec.title
    assert "not found" not in rec.title
    assert "no entry" not in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_uses_the_dict_provider(session: Session):
    """The dict-backed provider stands in for the host DB -- keyed by entry_key only."""
    entries = {
        expected_entry_key(_K_PATH, _APP, b"addr1"): b"one",
        expected_entry_key(_K_PATH, _APP, b"addr2"): b"two",
    }

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.get_entry(session, _APP, b"addr2", ward.dict_provider(entries))

    # the right one of the two, not just any
    assert "two" in rec.text
    assert "one" not in rec.text


# --- add / update -----------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_set_entry_add_shows_the_new_value(session: Session):
    """Writing a key the host does not hold is an ADD: nothing is being replaced, so the
    screen must not claim otherwise."""
    entries: dict[bytes, bytes] = {}

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_set_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = ward.set_entry(
            session, _APP, b"addr1", b"fresh", ward.dict_provider(entries)
        )

    assert res.success.message == "WARD write confirmed"
    assert "add entry" in rec.title
    assert "fresh" in rec.text
    assert "replaces" not in rec.text.lower()

    # the device confirmed; applying it is the host's job, under the key it was given --
    # which the host could not have computed for itself
    entries[res.entry_key] = b"fresh"
    assert entries == {expected_entry_key(_K_PATH, _APP, b"addr1"): b"fresh"}


@pytest.mark.models("core")
def test_ward_set_entry_update_names_the_value_it_replaces(session: Session):
    """Writing a key the host already holds is an OVERWRITE. Silently replacing a value
    the user cannot see is the failure mode this screen exists to prevent, so BOTH the
    old and the new value must be on screen."""
    key = expected_entry_key(_K_PATH, _APP, b"addr1")
    entries = {key: b"old_label"}

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_set_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = ward.set_entry(
            session, _APP, b"addr1", b"new_label", ward.dict_provider(entries)
        )

    assert "update entry" in rec.title
    # the old value is not merely present, it is labelled as the one being replaced
    assert "replaces" in rec.text.lower()
    assert "old_label" in rec.text
    assert "new_label" in rec.text

    # the write lands on the SAME key it read from -- an update, not a second entry
    assert res.entry_key == key
    entries[res.entry_key] = b"new_label"
    assert entries == {key: b"new_label"}


@pytest.mark.models("core")
def test_ward_set_entry_accepts_an_empty_value(session: Session):
    """b"" is a legitimate value to write -- distinct from not specifying one."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_set_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.set_entry(session, _APP, b"addr1", b"", lambda _k: None)

    assert "add entry" in rec.title


@pytest.mark.models("core")
def test_ward_set_entry_rejects_an_absent_value(session: Session):
    """...whereas an absent value is refused, rather than silently blanking the entry.

    This fails before the pull, so there is no input flow and no screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="value is required"):
        ward.set_entry(session, _APP, b"addr1", None, lambda _k: b"x")


# --- delete -----------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_delete_entry_names_the_value_being_removed(session: Session):
    """Confirming a deletion by key alone tells the user nothing about what they lose,
    so the device pulls the entry and puts its value on screen."""
    doomed = expected_entry_key(_K_PATH, _APP, b"addr1")
    keep = expected_entry_key(_K_PATH, _APP, b"addr2")
    entries = {doomed: b"doomed_label", keep: b"keep_me"}

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_delete_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = ward.delete_entry(session, _APP, b"addr1", ward.dict_provider(entries))

    assert res.success.message == "WARD delete confirmed"
    assert "delete entry" in rec.title
    # the value is labelled as the one being removed, not just shown
    assert "deleting value" in rec.text.lower()
    assert "doomed_label" in rec.text

    # the device confirmed; the host performs the removal -- and only of that one entry
    assert res.entry_key == doomed
    del entries[res.entry_key]
    assert entries == {keep: b"keep_me"}


@pytest.mark.models("core")
def test_ward_delete_entry_refuses_when_the_host_holds_nothing(session: Session):
    """The host asked to delete an entry and then, answering the pull, said it holds no
    such entry. That is a contradiction, so the device refuses rather than returning a
    Success the host could bank as a completed delete.

    Delete is deliberately NOT idempotent here: a no-op delete is a host bug worth
    surfacing. The failure arrives after the pull but before any screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="no such entry"):
        ward.delete_entry(session, _APP, b"ghost", lambda _k: None)


@pytest.mark.models("core")
def test_ward_delete_entry_deletes_an_empty_valued_entry(session: Session):
    """An entry whose value is empty still exists, so deleting it must be allowed --
    the absent/empty distinction has to hold on this path too, or empty entries become
    undeletable."""
    entries = {expected_entry_key(_K_PATH, _APP, b"addr1"): b""}

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_delete_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = ward.delete_entry(session, _APP, b"addr1", ward.dict_provider(entries))

    assert "delete entry" in rec.title

    del entries[res.entry_key]
    assert entries == {}


# --- shared validation ------------------------------------------------------------


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda s: ward.get_entry(s, _APP, b"", lambda _k: b"x"), id="get"),
        pytest.param(
            lambda s: ward.set_entry(s, _APP, b"", b"v", lambda _k: b"x"), id="set"
        ),
        pytest.param(
            lambda s: ward.delete_entry(s, _APP, b"", lambda _k: b"x"), id="delete"
        ),
        pytest.param(
            lambda s: ward.get_entry(s, "", b"addr1", lambda _k: b"x"), id="get-no-app"
        ),
    ],
)
def test_ward_rejects_an_incomplete_key(session: Session, call):
    """Every request validates (app_id, identifier) before deriving, pulling or showing.

    The wire fields are `optional` on purpose -- a proto2 `required` field a caller
    forgets to set is an encode-time failure in every binding, which has bitten this
    protocol before -- so the check has to live in the handler. It fails before any
    screen, hence no input flow.
    """
    with pytest.raises(exceptions.TrezorFailure, match="required"):
        call(session)
