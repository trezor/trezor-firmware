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

"""WARD: sealed two-part leaf, PULL-only, keyed path.

The device holds nothing. It derives an opaque 32-byte `entry_key` from a seed the host
does not have, asks the host for the leaf at THAT path, and displays what comes back. The
host's store is keyed by the opaque key and holds two sealed blobs -- no identifier and no
value anywhere in it.

These tests assert five separable things:
  - the pull happens, and names only the opaque key (protocol);
  - the key is the RIGHT one, i.e. the actual HMAC of the scope (crypto, via the
    test-only oracle in `tests/ward_keys.py`);
  - a leaf the device built survives a round trip through the host and decodes back to
    the same value (framing);
  - what the host holds reveals nothing, and a leaf that was tampered with or served from
    another path is REJECTED (confidentiality and authenticity);
  - the screen still warns, because sealing proves a value authentic without proving it
    current (UI).

The host never builds a leaf -- it cannot, having none of the keys -- so entries are
created by asking the device, which is also how a real host must work.
"""

import pytest

from trezorlib import exceptions, ward
from trezorlib import messages as m
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_keys import (
    bip39_seed,
    derive_k_data,
    derive_k_ident,
    derive_k_path,
    open_content,
    open_identity,
    unpack_content,
    unpack_identity,
)
from ...ward_keys import entry_key as expected_entry_key

_APP = "TEST"

# The device under test is set up with the default mnemonic and no passphrase
# (`SetupParams` in tests/conftest.py), so the oracle can reproduce its keys.
_SEED = bip39_seed(" ".join(["all"] * 12))
_K_PATH = derive_k_path(_SEED)
_K_IDENT = derive_k_ident(_SEED)
_K_DATA = derive_k_data(_SEED)


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


def _expected(br_name: str, final=m.Success) -> list:
    """The full PULL round: the device asks for the entry, we answer, then it confirms.

    Pinning the sequence is what proves the pull happened at the protocol level; the
    screen assertions only prove what was rendered. A read ends in Success; a write or
    delete ends in WARDLeafAck, because the host needs the leaf the device built.
    """
    return [m.WARDEntryRequest, m.ButtonRequest(name=br_name), final]


def _write(session: Session, store: dict, call, br_name: str) -> tuple:
    """Run a write/delete, walking its screen, and return (result, recorder)."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected(br_name, m.WARDLeafAck))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = call(ward.dict_provider(store))
    return res, rec


def _read(session: Session, store: dict, call) -> tuple:
    """Run a read, walking its screen, and return (result, recorder)."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = call(ward.dict_provider(store))
    return res, rec


def _seed(session: Session, store: dict, identifier: bytes, value: bytes) -> bytes:
    """Create an entry the only way a host can: ask the device to build the leaf.

    The host cannot synthesise one -- that is the point of the device being the encoder --
    so every fixture below goes through a real confirmed write.
    """
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, identifier, value, p),
        "ward_set_entry",
    )
    ward.apply(store, res)
    return res.entry_key


# --- the keyed path --------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_pull_names_only_the_opaque_key(session: Session):
    """The request must carry a 32-byte key and NOTHING that reveals the entry."""
    identifier = b"addr1"
    asked: list[bytes] = []

    def provider(entry_key: bytes):
        asked.append(entry_key)
        return None

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ward.get_entry(session, _APP, identifier, provider)

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
    res, _rec = _read(session, {}, lambda p: ward.get_entry(session, _APP, b"addr1", p))
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr1")


@pytest.mark.models("core")
def test_ward_pull_key_is_deterministic_and_domain_separated(session: Session):
    """Same (app_id, identifier) -> same key; different app_id -> different key.

    Determinism is what makes the store usable at all; domain separation is what stops
    one app's entry from resolving another's. Both are observable from the host side
    without any knowledge of the seed.
    """
    keys = [
        _read(session, {}, lambda p, a=app: ward.get_entry(session, a, b"addr1", p))[
            0
        ].entry_key
        for app in (_APP, _APP, "OTHER")
    ]
    first, again, other = keys
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
        ward.get_entry(session, "bad\x00app", b"addr1", lambda _k: None)


# --- the leaf ---------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_leaf_round_trips_through_the_host(session: Session):
    """A leaf the device built, stored verbatim by the host, decodes back to the same
    value when the device reads it again.

    This is the framing assertion: it would fail on any disagreement between the
    device's encode and decode paths, or on the host mangling what it stored.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"Petr_label")

    assert list(store) == [key]
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))
    assert "Petr_label" in rec.text


@pytest.mark.models("core")
def test_ward_leaf_is_sealed_and_hides_what_it_holds(session: Session):
    """What the host ends up holding must reveal neither the identifier nor the value.

    This is the confidentiality property, asserted on the actual stored bytes rather than
    inferred from the encoding byte -- a build that set encoding=0 while forgetting to
    seal would pass a weaker check.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"Petr_label")
    leaf = store[key]

    # both parts sealed: the encrypted arm is set, the readable arm is not
    for part in (leaf.identity, leaf.content):
        assert (part.encoding or 0) == 0
    assert leaf.identity.encrypted is not None and leaf.identity.plain is None
    assert leaf.content.encrypted is not None and leaf.content.plaintext is None
    assert len(leaf.identity.encrypted.nonce) == 12
    assert len(leaf.identity.encrypted.tag) == 16

    # key_type stays clear -- it has to, since it selects the keys that open the parts
    assert leaf.identity.key_type == "address"

    blob = leaf.identity.encrypted.ct + leaf.content.encrypted.ct
    assert b"addr1" not in blob
    assert b"Petr_label" not in blob
    assert _APP.encode() not in blob


@pytest.mark.models("core")
def test_ward_sealed_leaf_really_contains_the_preimage(session: Session):
    """...and it is genuinely the right plaintext under there, not just opaque bytes.

    Opened with the test-only oracle; a real host holds neither key. The identity part
    has no reader on the device either -- it already knows the identifier, having derived
    the path from it -- so this is currently the only thing that looks inside it. It is
    populated now so the leaf reaches its final shape before anything hashes it.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"Petr_label")
    leaf = store[key]

    identity = open_identity(_K_IDENT, key, "address", leaf.identity.encrypted)
    assert unpack_identity(identity) == (b"addr1", _APP.encode(), 0)

    content = open_content(_K_DATA, key, "address", leaf.content.encrypted)
    assert unpack_content(content) == (0, b"Petr_label")  # C_leaf unused for now


@pytest.mark.models("core")
def test_ward_sealed_part_is_bound_to_its_path(session: Session):
    """A leaf sealed for one path cannot be opened as another's.

    That binding is what stops a host from answering a request for one entry with a
    different entry's leaf -- a swap the keyed path alone would not catch, since the host
    chooses which stored bytes to hand back.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"Petr_label")
    other_key = expected_entry_key(_K_PATH, _APP, b"addr2")

    with pytest.raises(Exception):
        open_content(_K_DATA, other_key, "address", store[key].content.encrypted)


@pytest.mark.models("core")
def test_ward_delete_returns_a_leaf_with_both_parts_empty(session: Session):
    """A full delete, not a tombstone: the host removes the record entirely.

    The reference keeps the identity part alive on delete, which leaves behind a record
    of which entries once existed.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"doomed")

    res, _rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    assert res.entry_key == key
    assert res.leaf is not None
    # An empty part carries nothing, so there is nothing to seal and its encoding byte is
    # immaterial -- it is plaintext-encoded even in a sealed build. The codec has to accept
    # that, or a build would reject its own delete leaf.
    assert res.leaf.content.plaintext.content == b""
    assert res.leaf.identity.plain.identifier is None

    ward.apply(store, res)
    assert store == {}


@pytest.mark.models("core")
def test_ward_rejects_a_tampered_leaf(session: Session):
    """A leaf the host edited fails the tag check ON THE DEVICE.

    This is the first thing in the whole subsystem the device can actually REJECT. Before
    sealing, any bytes the host returned were accepted and displayed.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"Petr_label")

    sealed = store[key].content.encrypted
    flipped = bytes([sealed.ct[0] ^ 1]) + sealed.ct[1:]
    store[key] = ward.Leaf(
        store[key].identity,
        m.LeafContent(
            encoding=0,
            encrypted=m.EncryptedLeaf(nonce=sealed.nonce, tag=sealed.tag, ct=flipped),
        ),
    )

    with pytest.raises(exceptions.TrezorFailure, match="tag mismatch"):
        ward.get_entry(session, _APP, b"addr1", ward.dict_provider(store))


@pytest.mark.models("core")
def test_ward_rejects_a_leaf_served_from_another_path(session: Session):
    """The host answers a request for one entry with a different entry's real leaf.

    Every byte is authentic -- it is a leaf this device sealed -- so only the AAD's
    binding to entry_key catches it. The keyed path alone could not: the host chooses
    which stored bytes to hand back.
    """
    store: dict[bytes, ward.Leaf] = {}
    key1 = _seed(session, store, b"addr1", b"one")
    key2 = _seed(session, store, b"addr2", b"two")

    swapped = {key1: store[key2]}
    with pytest.raises(exceptions.TrezorFailure, match="tag mismatch"):
        ward.get_entry(session, _APP, b"addr1", ward.dict_provider(swapped))


# --- read -------------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_get_entry_pulls_and_shows(session: Session):
    """The device pulls the value from the host and renders it."""
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"Petr_label")

    res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))

    assert res.entry_key == key
    assert res.response.message == "WARD entry shown"
    assert res.leaf is None  # a read builds no leaf

    assert "unverified entry" in rec.title
    assert "Petr_label" in rec.text
    # the warning narrowed when the leaf was sealed -- the value is now authentic, but its
    # freshness is still unproven, and the screen has to say which of the two it means
    assert "not proven current" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_absent_is_distinct_from_empty(session: Session):
    """A missing entry (provider returns None) must not look like an entry whose value
    happens to be empty: the device says it was not found."""
    _res, rec = _read(session, {}, lambda p: ward.get_entry(session, _APP, b"nope", p))

    assert "entry not found" in rec.title
    assert "no entry" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_empty_value_is_shown_as_an_entry(session: Session):
    """The converse of the above, end to end: a present-but-empty value IS an entry.

    This is the assertion that pins the divergence from the reference, which encodes any
    empty value as an empty part -- i.e. as a delete -- and so could not represent this
    state at all. The value survives a real write and a real read.
    """
    store: dict[bytes, ward.Leaf] = {}
    _seed(session, store, b"addr1", b"")
    assert len(store) == 1  # an empty value is a STORED entry, not a deletion

    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))

    assert "unverified entry" in rec.title
    assert "not found" not in rec.title
    assert "no entry" not in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_serves_the_right_one_of_several(session: Session):
    """The store holds several leaves under opaque keys and serves the one asked for."""
    store: dict[bytes, ward.Leaf] = {}
    _seed(session, store, b"addr1", b"one")
    _seed(session, store, b"addr2", b"two")
    assert len(store) == 2

    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr2", p))

    assert "two" in rec.text
    assert "one" not in rec.text


# --- add / update -----------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_set_entry_add_shows_the_new_value(session: Session):
    """Writing a key the host does not hold is an ADD: nothing is being replaced, so the
    screen must not claim otherwise."""
    store: dict[bytes, ward.Leaf] = {}

    res, rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"fresh", p),
        "ward_set_entry",
    )

    assert "add entry" in rec.title
    assert "fresh" in rec.text
    assert "replaces" not in rec.text.lower()

    # the device built the leaf; storing it is the host's job, under the key it was given
    # -- which the host could not have computed for itself
    ward.apply(store, res)
    assert list(store) == [expected_entry_key(_K_PATH, _APP, b"addr1")]


@pytest.mark.models("core")
def test_ward_set_entry_update_names_the_value_it_replaces(session: Session):
    """Writing a key the host already holds is an OVERWRITE. Silently replacing a value
    the user cannot see is the failure mode this screen exists to prevent, so BOTH the
    old and the new value must be on screen.

    The old value is read back out of a leaf the device built earlier, so this also
    proves the decode path against real stored bytes rather than a fixture.
    """
    store: dict[bytes, ward.Leaf] = {}
    key = _seed(session, store, b"addr1", b"old_label")

    res, rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"new_label", p),
        "ward_set_entry",
    )

    assert "update entry" in rec.title
    # the old value is not merely present, it is labelled as the one being replaced
    assert "replaces" in rec.text.lower()
    assert "old_label" in rec.text
    assert "new_label" in rec.text

    # the write lands on the SAME key it read from -- an update, not a second entry
    assert res.entry_key == key
    ward.apply(store, res)
    assert list(store) == [key]


@pytest.mark.models("core")
def test_ward_set_entry_rejects_an_absent_value(session: Session):
    """An absent value is refused, rather than silently blanking the entry.

    This fails before the pull, so there is no input flow and no screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="value is required"):
        ward.set_entry(session, _APP, b"addr1", None, lambda _k: None)


# --- delete -----------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_delete_entry_names_the_value_being_removed(session: Session):
    """Confirming a deletion by key alone tells the user nothing about what they lose,
    so the device pulls the entry and puts its value on screen."""
    store: dict[bytes, ward.Leaf] = {}
    doomed = _seed(session, store, b"addr1", b"doomed_label")
    keep = _seed(session, store, b"addr2", b"keep_me")

    res, rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )

    assert res.entry_key == doomed
    assert "delete entry" in rec.title
    # the value is labelled as the one being removed, not just shown
    assert "deleting value" in rec.text.lower()
    assert "doomed_label" in rec.text

    # the device confirmed; the host performs the removal -- and only of that one entry
    ward.apply(store, res)
    assert list(store) == [keep]


@pytest.mark.models("core")
def test_ward_delete_entry_refuses_when_the_host_holds_nothing(session: Session):
    """The host asked to delete an entry and then, answering the pull, said it holds no
    such entry. That is a contradiction, so the device refuses rather than returning a
    leaf the host could bank as a completed delete.

    Delete is deliberately NOT idempotent here: a no-op delete is a host bug worth
    surfacing. The failure arrives after the pull but before any screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="no such entry"):
        ward.delete_entry(session, _APP, b"ghost", lambda _k: None)


@pytest.mark.models("core")
def test_ward_delete_entry_deletes_an_empty_valued_entry(session: Session):
    """An entry whose value is empty still exists, so deleting it must be allowed.

    The absent/empty distinction has to hold on this path too, or empty entries become
    undeletable -- the device would refuse, reading "empty" as "not there".
    """
    store: dict[bytes, ward.Leaf] = {}
    _seed(session, store, b"addr1", b"")

    res, rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )

    assert "delete entry" in rec.title
    ward.apply(store, res)
    assert store == {}


# --- shared validation ------------------------------------------------------------


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda s: ward.get_entry(s, _APP, b"", lambda _k: None), id="get"),
        pytest.param(
            lambda s: ward.set_entry(s, _APP, b"", b"v", lambda _k: None), id="set"
        ),
        pytest.param(
            lambda s: ward.delete_entry(s, _APP, b"", lambda _k: None), id="delete"
        ),
        pytest.param(
            lambda s: ward.get_entry(s, "", b"addr1", lambda _k: None), id="get-no-app"
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
