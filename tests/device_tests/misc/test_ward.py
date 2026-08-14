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

Once the device holds a root (seeded here by a debug-only message, standing in for the
attestation that will deliver one for real), the host must PROVE its answers: a present
leaf comes with a membership proof, an absent one with a witness. That is what finally
makes a stale or suppressed entry detectable.

These tests assert six separable things:
  - the pull happens, and names only the opaque key (protocol);
  - the key is the RIGHT one, i.e. the actual HMAC of the scope (crypto, via the
    test-only oracle in `tests/ward_keys.py`);
  - a leaf the device built survives a round trip through the host and decodes back to
    the same value (framing);
  - what the host holds reveals nothing, and a leaf that was tampered with or served from
    another path is REJECTED (confidentiality and authenticity);
  - a stale leaf or an unproved denial is REJECTED against the trusted root (freshness);
  - the screen still warns, because even a verified answer rides on a root nothing has
    attested yet (UI).

The host never builds a leaf -- it cannot, having none of the keys -- so entries are
created by asking the device, which is also how a real host must work.
"""

import pytest

from trezorlib import exceptions, ward
from trezorlib import messages as m
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent

from ...input_flows import InputFlowConfirmAllWarnings
from ...ward_trie import WardTrie
from ...ward_wm import MockWM
from ...ward_keys import (
    auth_commit,
    bip39_seed,
    derive_k_auth,
    derive_k_mac,
    derive_ward_id,
    root_mac,
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
_K_MAC = derive_k_mac(_SEED)
_K_AUTH = derive_k_auth(_SEED)

# A fixed wall-clock base for attestations. The device has no clock; it only ever compares
# what it was told last with what it is being told now.
_T0 = 1_700_000_000
_WARD_ID = derive_ward_id(_SEED)


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

    @property
    def squashed(self) -> str:
        """The body with all whitespace removed.

        A value long enough to WRAP gets a space inserted mid-token by the layout --
        `from_another_device` renders as `from_another_d evice` -- so a substring match on
        `text` fails for a reason that has nothing to do with what was shown.
        `text_content()` repairs hyphen-broken words but not plain wraps.

        Match VALUES here; match prose in `text`, where the spacing is the point.
        """
        return "".join("".join(self._texts).split())


def _expected(br_name: str, final=m.Success) -> list:
    """The full PULL round: the device asks for the entry, we answer, then it confirms.

    Pinning the sequence is what proves the pull happened at the protocol level; the
    screen assertions only prove what was rendered. A read ends in Success; a write or
    delete ends in WARDLeafAck, because the host needs the leaf the device built.
    """
    return [m.WARDEntryRequest, m.ButtonRequest(name=br_name), final]


def _write(session: Session, store: WardTrie, call, br_name: str) -> tuple:
    """Run a write/delete, walking its screen, and return (result, recorder)."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected(br_name, m.WARDLeafAck))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = call(ward.store_provider(store))
    return res, rec


def _read(session: Session, store: WardTrie, call) -> tuple:
    """Run a read, walking its screen, and return (result, recorder)."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry"))
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        res = call(ward.store_provider(store))
    return res, rec


def _publish(wm: MockWM, res) -> None:
    """Hand the WM what the write produced.

    A real host does exactly this: the device is the counter authority and the WM records
    what it is told. Skipping it leaves the device ahead of the WM, which is a refused
    sync rather than a lost write.
    """
    wm.publish(_WARD_ID, res.counter, res.mac, _T0 + res.counter)


def _seed(session: Session, store: WardTrie, identifier: bytes, value: bytes) -> bytes:
    """Create an entry the only way a host can: ask the device to build the leaf.

    The host cannot synthesise one -- that is the point of the device being the encoder --
    so every fixture below goes through a real confirmed write.

    The device derives and records its own root as part of that write, so there is nothing
    to tell it afterwards.
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
        return ward.Answer()

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
    res, _rec = _read(session, WardTrie(), lambda p: ward.get_entry(session, _APP, b"addr1", p))
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr1")


@pytest.mark.models("core")
def test_ward_pull_key_is_deterministic_and_domain_separated(session: Session):
    """Same (app_id, identifier) -> same key; different app_id -> different key.

    Determinism is what makes the store usable at all; domain separation is what stops
    one app's entry from resolving another's. Both are observable from the host side
    without any knowledge of the seed.
    """
    keys = [
        _read(session, WardTrie(), lambda p, a=app: ward.get_entry(session, a, b"addr1", p))[
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
        ward.get_entry(session, "bad\x00app", b"addr1", lambda _k: ward.Answer())


# --- the leaf ---------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_leaf_round_trips_through_the_host(session: Session):
    """A leaf the device built, stored verbatim by the host, decodes back to the same
    value when the device reads it again.

    This is the framing assertion: it would fail on any disagreement between the
    device's encode and decode paths, or on the host mangling what it stored.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"Petr_label")

    assert list(store.blobs) == [key]
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))
    assert "Petr_label" in rec.text


@pytest.mark.models("core")
def test_ward_leaf_is_sealed_and_hides_what_it_holds(session: Session):
    """What the host ends up holding must reveal neither the identifier nor the value.

    This is the confidentiality property, asserted on the actual stored bytes rather than
    inferred from the encoding byte -- a build that set encoding=0 while forgetting to
    seal would pass a weaker check.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"Petr_label")
    leaf = store.blobs[key]

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
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"Petr_label")
    leaf = store.blobs[key]

    identity = open_identity(_K_IDENT, key, "address", leaf.identity.encrypted)
    assert unpack_identity(identity) == (b"addr1", _APP.encode(), 0)

    content = open_content(_K_DATA, key, "address", leaf.content.encrypted)
    c_leaf, value = unpack_content(content)
    assert value == b"Petr_label"
    # the leaf is stamped with the counter it was written at, so a later per-leaf
    # staleness check has something to compare; nothing reads it yet
    assert c_leaf >= 1


@pytest.mark.models("core")
def test_ward_sealed_part_is_bound_to_its_path(session: Session):
    """A leaf sealed for one path cannot be opened as another's.

    That binding is what stops a host from answering a request for one entry with a
    different entry's leaf -- a swap the keyed path alone would not catch, since the host
    chooses which stored bytes to hand back.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"Petr_label")
    other_key = expected_entry_key(_K_PATH, _APP, b"addr2")

    with pytest.raises(Exception):
        open_content(_K_DATA, other_key, "address", store.blobs[key].content.encrypted)


@pytest.mark.models("core")
def test_ward_delete_returns_a_leaf_with_both_parts_empty(session: Session):
    """A full delete, not a tombstone: the host removes the record entirely.

    The reference keeps the identity part alive on delete, which leaves behind a record
    of which entries once existed.
    """
    store = WardTrie()
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
    assert len(store) == 0


@pytest.mark.models("core")
def test_ward_rejects_a_tampered_leaf(session: Session):
    """A leaf the host edited is refused.

    Two layers would each catch this and the ROOT gets there first, because a changed
    ciphertext changes the leaf hash. That makes the tag unreachable on this path, so the
    seal itself is pinned by the unit tests (`TestWardSealedLeaf`) rather than here; what
    this asserts is that the device refuses at all.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"Petr_label")

    sealed = store.blobs[key].content.encrypted
    flipped = bytes([sealed.ct[0] ^ 1]) + sealed.ct[1:]
    store.set(key, ward.Leaf(
        store.blobs[key].identity,
        m.LeafContent(
            encoding=0,
            encrypted=m.EncryptedLeaf(nonce=sealed.nonce, tag=sealed.tag, ct=flipped),
        ),
    ))

    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(session, _APP, b"addr1", ward.store_provider(store))


@pytest.mark.models("core")
def test_ward_rejects_a_leaf_served_from_another_path(session: Session):
    """The host answers a request for one entry with a different entry's real leaf.

    Every byte is authentic -- this device sealed it -- so neither the keyed path nor the
    ciphertext is wrong; only its POSITION is. The root catches it here (the leaf is not at
    that path in the tree), and the AAD binding would too. The keyed path alone could not:
    the host chooses which stored bytes to hand back.
    """
    store = WardTrie()
    key1 = _seed(session, store, b"addr1", b"one")
    key2 = _seed(session, store, b"addr2", b"two")

    swapped = WardTrie()
    swapped.set(key1, store.blobs[key2])
    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(session, _APP, b"addr1", ward.store_provider(swapped))


# --- read -------------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_get_entry_pulls_and_shows(session: Session):
    """The device pulls the value from the host and renders it."""
    store = WardTrie()
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
    _res, rec = _read(session, WardTrie(), lambda p: ward.get_entry(session, _APP, b"nope", p))

    assert "entry not found" in rec.title
    assert "no entry" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_empty_value_is_shown_as_an_entry(session: Session):
    """The converse of the above, end to end: a present-but-empty value IS an entry.

    This is the assertion that pins the divergence from the reference, which encodes any
    empty value as an empty part -- i.e. as a delete -- and so could not represent this
    state at all. The value survives a real write and a real read.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"")
    assert len(store) == 1  # an empty value is a STORED entry, not a deletion

    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))

    assert "unverified entry" in rec.title
    assert "not found" not in rec.title
    assert "no entry" not in rec.text.lower()


@pytest.mark.models("core")
def test_ward_get_entry_serves_the_right_one_of_several(session: Session):
    """The store holds several leaves under opaque keys and serves the one asked for."""
    store = WardTrie()
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
    store = WardTrie()

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
    assert list(store.blobs) == [expected_entry_key(_K_PATH, _APP, b"addr1")]


@pytest.mark.models("core")
def test_ward_set_entry_update_names_the_value_it_replaces(session: Session):
    """Writing a key the host already holds is an OVERWRITE. Silently replacing a value
    the user cannot see is the failure mode this screen exists to prevent, so BOTH the
    old and the new value must be on screen.

    The old value is read back out of a leaf the device built earlier, so this also
    proves the decode path against real stored bytes rather than a fixture.
    """
    store = WardTrie()
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
    assert list(store.blobs) == [key]


@pytest.mark.models("core")
def test_ward_set_entry_rejects_an_absent_value(session: Session):
    """An absent value is refused, rather than silently blanking the entry.

    This fails before the pull, so there is no input flow and no screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="value is required"):
        ward.set_entry(session, _APP, b"addr1", None, lambda _k: ward.Answer())


# --- delete -----------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_delete_entry_names_the_value_being_removed(session: Session):
    """Confirming a deletion by key alone tells the user nothing about what they lose,
    so the device pulls the entry and puts its value on screen."""
    store = WardTrie()
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
    assert list(store.blobs) == [keep]


@pytest.mark.models("core")
def test_ward_delete_entry_refuses_when_the_host_holds_nothing(session: Session):
    """The host asked to delete an entry and then, answering the pull, said it holds no
    such entry. That is a contradiction, so the device refuses rather than returning a
    leaf the host could bank as a completed delete.

    Delete is deliberately NOT idempotent here: a no-op delete is a host bug worth
    surfacing. The failure arrives after the pull but before any screen.
    """
    with pytest.raises(exceptions.TrezorFailure, match="no such entry"):
        ward.delete_entry(session, _APP, b"ghost", lambda _k: ward.Answer())


@pytest.mark.models("core")
def test_ward_delete_entry_deletes_an_empty_valued_entry(session: Session):
    """An entry whose value is empty still exists, so deleting it must be allowed.

    The absent/empty distinction has to hold on this path too, or empty entries become
    undeletable -- the device would refuse, reading "empty" as "not there".
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"")

    res, rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )

    assert "delete entry" in rec.title
    ward.apply(store, res)
    assert len(store) == 0


# --- shared validation ------------------------------------------------------------


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda s: ward.get_entry(s, _APP, b"", lambda _k: ward.Answer()), id="get"),
        pytest.param(
            lambda s: ward.set_entry(s, _APP, b"", b"v", lambda _k: ward.Answer()), id="set"
        ),
        pytest.param(
            lambda s: ward.delete_entry(s, _APP, b"", lambda _k: ward.Answer()), id="delete"
        ),
        pytest.param(
            lambda s: ward.get_entry(s, "", b"addr1", lambda _k: ward.Answer()), id="get-no-app"
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


# --- proofs against the trusted root ----------------------------------------------


@pytest.mark.models("core")
def test_ward_rejects_a_rolled_back_leaf(session: Session):
    """The host serves an OLDER version of an entry it really did hold once.

    Every byte is authentic -- this device sealed that leaf, for this very path -- so
    neither the keyed path nor the AEAD can catch it. Only the root can: the old leaf
    hashes to a root the device no longer trusts. This is the first time WARD can detect
    a rollback, and it is the reason a root is worth having at all.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"old_value")
    stale_leaf = store.blobs[key]

    # One applied update. The device derives a new root from it, so the leaf above is now
    # history -- and the store must be kept in step, or the NEXT pull would serve a proof
    # against a root the device has already moved past.
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"new_value", p),
        "ward_set_entry",
    )
    ward.apply(store, res)

    rolled_back = WardTrie()
    rolled_back.set(key, stale_leaf)
    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(session, _APP, b"addr1", ward.store_provider(rolled_back))


@pytest.mark.models("core")
def test_ward_rejects_an_unproved_denial(session: Session):
    """The host hides an entry by claiming it holds none.

    Suppression is the other half of what a root buys. Without a proof the device would
    have to take "no such entry" on trust, and a host could bury any entry it disliked.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"present")

    def denies_everything(_entry_key: bytes) -> ward.Answer:
        return ward.Answer()

    with pytest.raises(exceptions.TrezorFailure, match="witness"):
        ward.get_entry(session, _APP, b"addr1", denies_everything)


@pytest.mark.models("core")
def test_ward_rejects_a_membership_answer_without_a_proof(session: Session):
    """A leaf offered with no proof at all is refused once a root is held.

    TWO entries, not one: in a single-leaf tree the root IS the leaf hash, so the empty
    proof is the correct proof and withholding it proves nothing. This test only means
    something where a real proof would have had to be non-empty.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"present")
    _seed(session, store, b"addr2", b"other")
    assert len(store.membership_proof(key)) > 0  # the proof being withheld is real

    def no_proof(_entry_key: bytes) -> ward.Answer:
        return ward.Answer(leaf=store.blobs[key], proof=[])

    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(session, _APP, b"addr1", no_proof)


@pytest.mark.models("core")
def test_ward_accepts_a_proved_absence(session: Session):
    """The converse: a properly witnessed absence is accepted and shown as not found.

    Without this the rejection tests above would pass just as well on a device that
    refused every denial, which would be useless rather than secure.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"present")

    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"absent", p)
    )
    assert "entry not found" in rec.title


@pytest.mark.models("core")
def test_ward_verifies_a_present_entry_against_the_root(session: Session):
    """And a well-proved present entry still shows its value."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"Petr_label")

    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )
    assert "Petr_label" in rec.text


# --- the root outlives the session -------------------------------------------------


@pytest.mark.models("core")
def test_ward_root_survives_a_new_session(session: Session):
    """A root written in one session is still there in the next.

    This is what persistence buys. Before it, a device that lost its session verified
    nothing until the next write -- and "nothing is checked" reads exactly like ordinary
    operation, so it is the failure that hides. The second session performs NO write, so
    the only root it can be verifying against is the stored one.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"Petr_label")

    # via the test context, not session.client: that returns a bare ThpSession with no
    # debug plumbing, so the input flows and expected-response checks would not attach
    fresh = session.test_ctx.get_session()
    _res, rec = _read(
        fresh, store, lambda p: ward.get_entry(fresh, _APP, b"addr1", p)
    )
    assert "Petr_label" in rec.text

    # and it is really verifying: a rolled-back leaf is refused in the new session too
    stale = WardTrie()
    stale.set(
        expected_entry_key(_K_PATH, _APP, b"addr1"),
        store.blobs[expected_entry_key(_K_PATH, _APP, b"addr1")],
    )
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"moved_on", p),
        "ward_set_entry",
    )
    ward.apply(store, res)

    another = session.test_ctx.get_session()
    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(another, _APP, b"addr1", ward.store_provider(stale))


# NOTE: roots are stored PER HIDDEN WALLET, keyed by a passphrase-dependent wallet_id, and
# that isolation is covered at the storage level rather than here -- a device-level test
# would need `setup_client(passphrase=True)` and two explicit passphrases, and the keys the
# oracle in this file derives assume the default empty one. Worth adding, but it needs that
# fixture work first rather than a guess at it.


# --- the sync round: adopting a tree the device did not build ----------------------


def _subset(store: WardTrie, keys) -> WardTrie:
    """A trie holding some of `store`'s leaves -- a shape the device never computed.

    Assembled from leaves the device really did seal, so they still open; only the TREE is
    new. Building one by writing into a second empty store does not work: the device's root
    tracks whichever store it last wrote through, so a pull against the other one cannot
    produce a witness and fails before the test reaches its point.
    """
    out = WardTrie()
    for k in keys:
        out.set(k, store.blobs[k])
    out.counter = store.counter
    # NOTE: a subset holding every leaf of its source has the SAME root. Where a test
    # needs a genuinely different tree, assert that -- otherwise it can silently become a
    # test of the identical tree, which passes for the wrong reason.
    return out


def _attest(
    session: Session,
    wm: MockWM,
    store: WardTrie,
    counter: int | None = None,
    timestamp: int | None = None,
) -> None:
    """Run a full sync round: nonce, WM attestation, root.

    The WM is told the mac rather than computing it -- it holds no key and could not. That
    asymmetry is the whole point, so the helper preserves it rather than reaching into the
    store on the WM's behalf.
    """
    if counter is None:
        counter = store.counter
    if timestamp is None:
        timestamp = _T0 + counter  # time moves with the counter, as it would in practice
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, counter, store.root())
    wm.publish(ack.ward_id, counter, mac, timestamp)
    _c, _m, _t, sig = wm.attest(ack.ward_id, ack.nonce)
    ward.ingest_attestation(session, counter, mac, sig, timestamp)
    ward.reconcile(session, store.root())
    store.counter = counter  # device and store now agree
    store.timestamp = timestamp


@pytest.mark.models("core")
def test_ward_adopts_an_attested_tree_it_never_built(session: Session):
    """The device adopts a tree built somewhere else, and then verifies against it.

    This is what the sync round is for. `foreign` was never written through this device --
    it holds entries the device has no record of -- and after one attested round the
    device checks proofs against it and rejects its own former tree.

    (A genuinely blank device cannot be staged here: the root lives in flash keyed by
    wallet, so a new session inherits it. Adopting at a higher counter exercises the same
    path, and additionally shows a local tree being superseded -- the documented window
    where writes that never reached the WM are discarded.)
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"local_only")
    foreign_key = _seed(session, store, b"elsewhere", b"from_another_device")

    # a tree the device never built: the same leaves, minus one. It has to be attested
    # ABOVE the counter the device's own writes reached -- an older one is a rollback and
    # is refused, which is the whole point of the floor.
    foreign = _subset(store, [foreign_key])

    wm = MockWM()
    _attest(session, wm, foreign, counter=store.counter + 1)

    _res, rec = _read(
        session, foreign, lambda p: ward.get_entry(session, _APP, b"elsewhere", p)
    )
    assert "from_another_device" in rec.squashed  # long enough to wrap; see `squashed`
    assert foreign_key in foreign.blobs

    # ...and the entry the adopted tree does not contain is now provably absent, which the
    # device could not have concluded from a tree it computed itself
    _res, rec = _read(
        session, foreign, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )
    assert "entry not found" in rec.title


@pytest.mark.models("core")
def test_ward_refuses_an_attestation_from_the_wrong_signer(session: Session):
    """Only the provisioned WM key counts. Everything else about the message can be
    perfectly well-formed."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")

    impostor = MockWM(seed=b"NOT THE WARD MANAGER DEBUG KEY!!")
    counter = store.counter
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, counter, store.root())
    sig = impostor.sign(ack.ward_id, ack.nonce, counter, mac, _T0 + counter)

    with pytest.raises(exceptions.TrezorFailure, match="attestation verification failed"):
        ward.ingest_attestation(session, counter, mac, sig, _T0 + counter)


@pytest.mark.models("core")
def test_ward_refuses_an_attestation_bound_to_another_nonce(session: Session):
    """A stockpiled anchor is useless: the signature is bound to a nonce the device minted
    for THIS round, which the WM could not have known in advance.

    Without this a host could collect signed anchors while the network was in a state it
    liked and serve one whenever it suited.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = MockWM()

    # an anchor signed against an earlier round's nonce
    counter = store.counter
    stale_ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, counter, store.root())
    stale_sig = wm.sign(stale_ack.ward_id, stale_ack.nonce, counter, mac, _T0 + counter)

    ward.sync(session)  # a new round, a new nonce
    with pytest.raises(exceptions.TrezorFailure, match="attestation verification failed"):
        ward.ingest_attestation(session, counter, mac, stale_sig, _T0 + counter)


@pytest.mark.models("core")
def test_ward_refuses_a_root_that_does_not_match_the_attested_mac(session: Session):
    """The mac is what binds the WM's claim to actual contents.

    The attestation here is genuine and current; only the root is swapped. The host cannot
    produce a mac for a tree of its choosing -- K_mac never leaves the device -- so this is
    the substitution the mac exists to catch.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    other_key = _seed(session, store, b"addr2", b"w")
    other = _subset(store, [other_key])  # a different root; reconcile fails on the mac

    wm = MockWM()
    counter = store.counter
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, counter, store.root())
    wm.publish(ack.ward_id, counter, mac, _T0 + counter)
    _c, _m, _t, sig = wm.attest(ack.ward_id, ack.nonce)
    ward.ingest_attestation(session, counter, mac, sig, _T0 + counter)

    with pytest.raises(exceptions.TrezorFailure, match="does not match the attested mac"):
        ward.reconcile(session, other.root())


@pytest.mark.models("core")
def test_ward_refuses_an_attested_counter_below_the_floor(session: Session):
    """Anti-rollback. A WM cannot forge a mac, so its remaining freedom is to replay a
    state this wallet really did reach -- and the counter floor is what bounds which."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = MockWM()

    _attest(session, wm, store, counter=store.counter + 5)  # raise the floor

    behind = store.counter - 1
    ack = ward.sync(session)
    old_mac = root_mac(_K_MAC, _WARD_ID, behind, store.root())
    sig = wm.sign(ack.ward_id, ack.nonce, behind, old_mac, _T0 + behind)
    with pytest.raises(exceptions.TrezorFailure, match="older than the stored counter"):
        ward.ingest_attestation(session, behind, old_mac, sig, _T0 + behind)


@pytest.mark.models("core")
def test_ward_refuses_a_different_state_at_the_same_counter(session: Session):
    """One counter names one state.

    Roots repeat whenever contents repeat, so a counter is what distinguishes moments. If
    the WM attests the counter this device already holds, the state it names has to be the
    state the device already has -- otherwise one of them is wrong, and adopting either
    silently discards the other.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    other_key = _seed(session, store, b"addr9", b"other")
    wm = MockWM()
    _attest(session, wm, store)  # the device's real state, at its own counter

    # a DIFFERENT state offered at that same counter
    divergent = _subset(store, [other_key])
    counter = store.counter

    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, counter, divergent.root())
    sig = wm.sign(ack.ward_id, ack.nonce, counter, mac, _T0 + counter)
    ward.ingest_attestation(session, counter, mac, sig, _T0 + counter)
    with pytest.raises(exceptions.TrezorFailure, match="counter matches but the root differs"):
        ward.reconcile(session, divergent.root())


@pytest.mark.models("core")
def test_ward_reconcile_needs_an_attestation_first(session: Session):
    """A root on its own adopts nothing -- otherwise the host could simply announce one."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")

    ward.sync(session)  # round open, nothing attested
    with pytest.raises(exceptions.TrezorFailure, match="no attested sync round"):
        ward.reconcile(session, store.root())


@pytest.mark.models("core")
def test_ward_an_attestation_cannot_be_adopted_twice(session: Session):
    """The round closes on adoption, so a replayed reconcile has nothing to act on."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = MockWM()
    _attest(session, wm, store)

    with pytest.raises(exceptions.TrezorFailure, match="no attested sync round"):
        ward.reconcile(session, store.root())


# --- writes advance the counter -----------------------------------------------------


@pytest.mark.models("core")
def test_ward_a_write_advances_the_counter(session: Session):
    """Each confirmed write moves the counter on and hands back the pair to publish.

    Before this the counter only moved on a sync, so local writes were invisible to the
    WM and a later attestation at a higher counter silently replaced them.
    """
    store = WardTrie()
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"one", p),
        "ward_set_entry",
    )
    ward.apply(store, res)
    first = res.counter
    assert first is not None and first >= 1
    assert res.mac is not None

    res2, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr2", b"two", p),
        "ward_set_entry",
    )
    ward.apply(store, res2)
    assert res2.counter == first + 1


@pytest.mark.models("core")
def test_ward_a_published_write_syncs_cleanly(session: Session):
    """Publish what the write produced and the next sync is a no-op, not a conflict.

    Same counter, same root -- so the device accepts, and nothing is discarded. This is
    the round trip that closes the window the previous step had to document.
    """
    store = WardTrie()
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"kept", p),
        "ward_set_entry",
    )
    ward.apply(store, res)

    wm = MockWM()
    _publish(wm, res)

    ack = ward.sync(session)
    counter, mac, ts, sig = wm.attest(ack.ward_id, ack.nonce)
    ward.ingest_attestation(session, counter, mac, sig, ts)
    ward.reconcile(session, store.root())
    store.counter = counter  # device and store now agree

    # the entry survived the round trip
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))
    assert "kept" in rec.text


@pytest.mark.models("core")
def test_ward_an_unpublished_write_blocks_sync_rather_than_losing_it(session: Session):
    """A device ahead of the WM refuses to sync. It does NOT quietly adopt the older tree.

    This is the failure mode the counter advance buys: the write is still there, the sync
    fails closed, and publishing the pair the device handed back resolves it.
    """
    store = WardTrie()
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"unpublished", p),
        "ward_set_entry",
    )
    ward.apply(store, res)

    wm = MockWM()
    stale = _subset(store, [])  # the WM's view: the tree as it was before the write
    ack = ward.sync(session)
    behind = res.counter - 1
    mac = root_mac(_K_MAC, _WARD_ID, behind, stale.root())
    sig = wm.sign(ack.ward_id, ack.nonce, behind, mac, _T0 + behind)

    with pytest.raises(exceptions.TrezorFailure, match="older than the stored counter"):
        ward.ingest_attestation(session, behind, mac, sig, _T0 + behind)

    # ...and the write is still readable afterwards
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p))
    assert "unpublished" in rec.text


# --- catching up on transitions this device missed -----------------------------------


def _link(from_counter, from_root, to_counter, to_root):
    """A transition minted by "another device of this wallet".

    The oracle holds K_auth because it holds the seed, which is exactly what a second
    device would. That is what lets a single-emulator test exercise catch-up at all: this
    device is always at its own latest counter, so it can never fall behind itself.
    """
    return (
        from_counter,
        from_root,
        to_counter,
        to_root,
        auth_commit(_K_AUTH, _WARD_ID, from_counter, from_root, to_counter, to_root),
    )


@pytest.mark.models("core")
def test_ward_catches_up_across_transitions_it_never_saw(session: Session):
    """The device adopts a head two steps ahead, by verifying each step.

    Reconcile would take this head on the WM's word alone. The chain additionally shows
    every intervening step was authorised by a device of this wallet and that none was
    skipped -- so the head is on this wallet's history, not a fork of it.
    """
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    k2 = _seed(session, store, b"b", b"two")
    base_counter, base_root = store.counter, store.root()

    # two transitions made elsewhere while this device was away
    mid = _subset(store, [k1])
    head = _subset(store, [k2])
    links = [
        _link(base_counter, base_root, base_counter + 1, mid.root()),
        _link(base_counter + 1, mid.root(), base_counter + 2, head.root()),
    ]
    target = base_counter + 2

    wm = MockWM()
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, target, head.root())
    sig = wm.sign(ack.ward_id, ack.nonce, target, mac, _T0 + target)
    ward.ingest_attestation(session, target, mac, sig, _T0 + target)
    res = ward.verify_chain(session, links)

    assert res.counter == target
    assert res.new_root == head.root()

    # the adopted tree is the one it now verifies against
    head.counter = target
    _res, rec = _read(session, head, lambda p: ward.get_entry(session, _APP, b"b", p))
    assert "two" in rec.text


@pytest.mark.models("core")
def test_ward_refuses_a_chain_with_a_gap(session: Session):
    """A skipped step is how a fork stays invisible: every link is authentic, but the
    device never sees the transition that diverged."""
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    base_counter, base_root = store.counter, store.root()
    head = _subset(store, [k1])

    # jumps two counters in one link
    links = [_link(base_counter, base_root, base_counter + 2, head.root())]

    wm = MockWM()
    ack = ward.sync(session)
    target = base_counter + 2
    mac = root_mac(_K_MAC, _WARD_ID, target, head.root())
    sig = wm.sign(ack.ward_id, ack.nonce, target, mac, _T0 + target)
    ward.ingest_attestation(session, target, mac, sig, _T0 + target)

    with pytest.raises(exceptions.TrezorFailure, match="exactly one"):
        ward.verify_chain(session, links)


@pytest.mark.models("core")
def test_ward_refuses_a_chain_that_does_not_start_at_its_own_head(session: Session):
    """The baseline is the device's own head, never one the host names."""
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")
    head = _subset(store, [k1])
    # ...and it must genuinely differ, or the "wrong" baseline is the device's own head
    # and the chain verifies correctly -- a test that cannot fail for its stated reason
    assert head.root() != store.root()

    target = store.counter + 1
    # a link starting from a root this device is not at
    links = [_link(store.counter, head.root(), target, head.root())]

    wm = MockWM()
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, target, head.root())
    sig = wm.sign(ack.ward_id, ack.nonce, target, mac, _T0 + target)
    ward.ingest_attestation(session, target, mac, sig, _T0 + target)

    with pytest.raises(exceptions.TrezorFailure, match="does not follow the running root"):
        ward.verify_chain(session, links)


@pytest.mark.models("core")
def test_ward_refuses_an_unauthorised_link(session: Session):
    """Without K_auth a link cannot be minted, so the host cannot invent a step."""
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    base_counter, base_root = store.counter, store.root()
    head = _subset(store, [k1])
    target = base_counter + 1

    forged = [(base_counter, base_root, target, head.root(), bytes(32))]

    wm = MockWM()
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, target, head.root())
    sig = wm.sign(ack.ward_id, ack.nonce, target, mac, _T0 + target)
    ward.ingest_attestation(session, target, mac, sig, _T0 + target)

    with pytest.raises(exceptions.TrezorFailure, match="not authorised"):
        ward.verify_chain(session, forged)


@pytest.mark.models("core")
def test_ward_refuses_a_chain_that_ends_somewhere_else(session: Session):
    """Descent is not currency. A perfectly authorised chain to a DIFFERENT head than the
    one attested must still be refused, or the two guarantees would not compose."""
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    base_counter, base_root = store.counter, store.root()
    elsewhere = _subset(store, [k1])
    attested = _subset(store, [])
    # the whole point is that the chain ends somewhere the attestation did not name
    assert elsewhere.root() != attested.root()

    links = [_link(base_counter, base_root, base_counter + 1, elsewhere.root())]
    target = base_counter + 1

    wm = MockWM()
    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, target, attested.root())  # attests a different root
    sig = wm.sign(ack.ward_id, ack.nonce, target, mac, _T0 + target)
    ward.ingest_attestation(session, target, mac, sig, _T0 + target)

    with pytest.raises(exceptions.TrezorFailure, match="does not match the attested mac"):
        ward.verify_chain(session, links)


@pytest.mark.models("core")
def test_ward_a_write_emits_its_own_authorisation(session: Session):
    """Each write hands back the link that authorises it, and the host records it.

    Those links are what a device catching up later consumes; a host that dropped them
    could not prove its own history.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")

    assert len(store.links) == 2
    for from_counter, _fr, to_counter, _tr, ac in store.links:
        assert to_counter == from_counter + 1
        assert ac is not None and len(ac) == 32
    # ...and they chain: each link starts where the previous ended
    assert store.links[0][2] == store.links[1][0]
    assert store.links[0][3] == store.links[1][1]


# --- rollback: the escape from a stuck wallet ----------------------------------------


def _rollback(session: Session, store: WardTrie):
    """Undo the last transition, walking the confirmation screen."""
    from_counter, from_root, _tc, _tr, ac = store.links[-1]
    assert from_counter == store.counter - 1  # the link that made the current head
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_rollback"), m.WARDRollbackAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ack = ward.rollback(session, from_root, ac)
    return ack, rec


@pytest.mark.models("core")
def test_ward_rollback_undoes_the_last_write(session: Session):
    """The wallet returns to the state before its most recent change.

    The counter still goes FORWARD. Reusing it would let the undone write replay, since
    its own authorisation names that counter.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    before_root, before_counter = store.root(), store.counter
    key = _seed(session, store, b"b", b"two")

    ack, rec = _rollback(session, store)

    assert ack.counter == store.counter + 1  # forward, though the head moves back
    assert ack.new_root == before_root
    assert "revert" in rec.title.lower()
    assert "cannot be recovered" in rec.text.lower()

    # the device now verifies against the earlier tree, and the undone entry is gone
    rewound = _subset(store, [k for k in store.blobs if k != key])
    ward.apply_rollback(store, ack)
    rewound.counter = ack.counter
    assert rewound.root() == before_root
    _res, rec = _read(session, rewound, lambda p: ward.get_entry(session, _APP, b"b", p))
    assert "entry not found" in rec.title


@pytest.mark.models("core")
def test_ward_rollback_refuses_a_target_the_host_invents(session: Session):
    """The demotion target is whatever the authorisation names, never a root the host
    picks. This is the attack the whole construction exists to stop: a host that fakes a
    stuck state would otherwise rewind the wallet anywhere in its history."""
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")
    _from_counter, _from_root, _tc, _tr, ac = store.links[-1]

    invented = _subset(store, [])  # some other tree the host would prefer
    with pytest.raises(exceptions.TrezorFailure, match="does not describe the current head"):
        ward.rollback(session, invented.root(), ac)


@pytest.mark.models("core")
def test_ward_rollback_refuses_an_authorisation_for_an_older_step(session: Session):
    """THE counter-binding attack, from the design's own worked example.

    Roots repeat whenever contents repeat. An old authorisation whose `to_root` equals
    today's head would, if matched on the root alone, demote the wallet to a state from
    arbitrarily long ago -- in one hop, with the one-step rule perfectly satisfied. Naming
    the counter is what rejects it before the roots are even compared.
    """
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    # take the wallet away and back again, so an EARLIER counter has today's root
    _seed(session, store, b"b", b"two")
    repeated_root = store.root()
    old_link = store.links[-1]

    _write_and_apply = _seed(session, store, b"c", b"three")
    res, _rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"c", p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    assert store.root() == repeated_root  # same contents, so the same root as before

    # the old authorisation names that root, but at its own, older counter
    _fc, from_root, _tc, to_root, ac = old_link
    assert to_root == store.root()
    with pytest.raises(exceptions.TrezorFailure, match="does not describe the current head"):
        ward.rollback(session, from_root, ac)
    assert k1 in store.blobs


@pytest.mark.models("core")
def test_ward_rollback_unsticks_a_wallet_the_wm_never_saw(session: Session):
    """End to end: a write that never reached the WM blocks sync; undoing it unblocks."""
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    wm = MockWM()
    _attest(session, wm, store)  # WM and device agree here

    published_root, published_counter = store.root(), store.counter
    _seed(session, store, b"b", b"two")  # ...and this never reaches the WM

    ack_sync = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, published_counter, published_root)
    sig = wm.sign(ack_sync.ward_id, ack_sync.nonce, published_counter, mac, _T0 + published_counter)
    with pytest.raises(exceptions.TrezorFailure, match="older than the stored counter"):
        ward.ingest_attestation(session, published_counter, mac, sig, _T0 + published_counter)

    ack, _rec = _rollback(session, store)
    ward.apply_rollback(store, ack)

    # the wallet is back on the published contents, at a counter beyond the stuck one
    assert ack.new_root == published_root
    assert ack.counter > published_counter


# --- the clock, and the way back from it -------------------------------------------


def _recover(session: Session, wm: MockWM, counter: int, mac: bytes, timestamp: int):
    """Walk the recovery confirmation and return (ack, recorder)."""
    ack_sync = ward.sync(session)
    sig = wm.sign(ack_sync.ward_id, ack_sync.nonce, counter, mac, timestamp)
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_recover_counter"), m.WARDRecoverCounterAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get())
        ack = ward.recover_counter(session, counter, mac, sig, timestamp)
    return ack, rec


@pytest.mark.models("core")
def test_ward_ingest_refuses_an_attestation_from_before_the_stored_time(session: Session):
    """A WM whose clock ran backwards is refused even when its counter did not.

    That combination is what a restore-from-backup looks like from the device's side when
    the operator's counter register survived but the clock did not, and it is the only
    thing the timestamp catches that the counter does not. Attested at the SAME counter,
    so the anti-rollback check cannot be what fires -- otherwise this test would pass on a
    build with no timestamp handling at all.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = MockWM()
    _attest(session, wm, store)

    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, store.counter, store.root())
    long_ago = store.timestamp - 86400
    sig = wm.sign(ack.ward_id, ack.nonce, store.counter, mac, long_ago)
    with pytest.raises(exceptions.TrezorFailure, match="older than the stored time"):
        ward.ingest_attestation(session, store.counter, mac, sig, long_ago)


@pytest.mark.models("core")
def test_ward_ingest_tolerates_clock_jitter(session: Session):
    """...but a small backward step is ordinary NTP correction, not an incident.

    The allowance is EPSILON_SECONDS. Without it every clock nudge on the WM would turn
    into a support ticket, and the check would be tuned into uselessness by whoever had to
    field them.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = MockWM()
    _attest(session, wm, store)

    # inside the allowance, and deliberately not equal to it -- an off-by-one on the
    # boundary is not what this test is about
    _attest(session, wm, store, timestamp=store.timestamp - 60)


@pytest.mark.models("core")
def test_ward_recover_counter_accepts_a_backward_attestation(session: Session):
    """The way back from a WM that lost its register: an older head, with consent.

    Monotonicity is what stops a replay, and when the operator's state is genuinely lost
    it becomes a lock-out instead -- every device refuses every sync forever. This is the
    only path that accepts a lower counter, and afterwards the wallet syncs again.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    wm = MockWM()
    _attest(session, wm, store)
    old_counter, old_root, old_time = store.counter, store.root(), store.timestamp
    old_mac = root_mac(_K_MAC, _WARD_ID, old_counter, old_root)

    res, _rec = _write(
        session, store, lambda p: ward.set_entry(session, _APP, b"b", b"two", p), "ward_set_entry"
    )
    ward.apply(store, res)
    _attest(session, wm, store)
    assert store.counter > old_counter

    # the WM comes back from a backup: it now says the old head is current
    ack, _rec = _recover(session, wm, old_counter, old_mac, old_time - 3600)
    assert ack.counter == old_counter

    # ...and the device adopts it, so the wallet is usable again
    ward.reconcile(session, old_root)
    rewound = _subset(store, [expected_entry_key(_K_PATH, _APP, b"a")])
    assert rewound.root() == old_root
    _res, rec = _read(session, rewound, lambda p: ward.get_entry(session, _APP, b"a", p))
    assert "one" in rec.text


@pytest.mark.models("core")
def test_ward_recover_counter_refuses_an_attestation_that_is_not_older(session: Session):
    """Recovery is for going backwards, and nothing else.

    An ordinary attestation routed through here would work perfectly well and cost the
    user a hold-to-confirm every sync, which is how a screen stops being read. The refusal
    keeps this prompt rare enough to still mean something when it appears.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    wm = MockWM()
    _attest(session, wm, store)

    ack = ward.sync(session)
    mac = root_mac(_K_MAC, _WARD_ID, store.counter, store.root())
    sig = wm.sign(ack.ward_id, ack.nonce, store.counter, mac, store.timestamp)
    with pytest.raises(exceptions.TrezorFailure, match="not older"):
        ward.recover_counter(session, store.counter, mac, sig, store.timestamp)


@pytest.mark.models("core")
def test_ward_recover_counter_still_requires_a_genuine_attestation(session: Session):
    """Consent does not replace verification.

    The user's approval covers "go back to this state", not "trust whoever said so": the
    signature is checked against this round's nonce exactly as on the ordinary path, and
    it fails before any screen -- so no input flow here.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    wm = MockWM()
    _attest(session, wm, store)
    behind = store.counter - 1
    mac = root_mac(_K_MAC, _WARD_ID, behind, store.root())

    impostor = MockWM(seed=b"NOT THE WARD MANAGER DEBUG KEY!!")
    ack = ward.sync(session)
    sig = impostor.sign(ack.ward_id, ack.nonce, behind, mac, store.timestamp - 3600)
    with pytest.raises(exceptions.TrezorFailure, match="attestation verification failed"):
        ward.recover_counter(session, behind, mac, sig, store.timestamp - 3600)


@pytest.mark.models("core")
def test_ward_recover_counter_screen_names_both_counters_and_the_distance(session: Session):
    """The screen has to carry the decision, because the crypto cannot.

    Everything presented here is authentic whether the operator is recovering or an
    attacker is rewinding -- a replayed (counter, mac) pair is proof this wallet really did
    reach that state, and says nothing about who is replaying it. The only thing that
    separates the two cases is whether the user means it, so the prompt names where the
    wallet is, where it is going, and how far back that is.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    wm = MockWM()
    _attest(session, wm, store)
    behind = store.counter - 1
    mac = root_mac(_K_MAC, _WARD_ID, behind, store.root())

    _ack, rec = _recover(session, wm, behind, mac, store.timestamp - 7200)

    assert "reset sync counter" in rec.title
    assert "#%d" % store.counter in rec.squashed  # where it is
    assert "#%d" % behind in rec.squashed  # where it is going
    assert "hours" in rec.text  # and how far back
    assert "may be lost" in rec.text


# --- the sibling a delete promotes, and the tree a delete can empty ----------------


def _branch_sibling_case(session: Session):
    """A store where deleting one entry collapses a branch whose sibling is a BRANCH.

    Built by real writes, so the keys are whatever the device's HMAC produces -- the shape
    is discovered rather than constructed, and the helper says so if this seed stops
    producing one, instead of quietly testing the easy case.
    """
    store = WardTrie()
    for i in range(6):
        _seed(session, store, b"addr%d" % i, b"v%d" % i)
        for key in list(store.blobs):
            if store.sibling_decomposition(key) is not None:
                return store, key
    pytest.skip("no branch-sibling delete arises for this seed")


@pytest.mark.models("core")
def test_ward_delete_refuses_a_sibling_it_cannot_classify(session: Session):
    """A delete whose answer identifies the sibling in NEITHER form is refused.

    The proof carries only the sibling's hash, which does not say whether it is a leaf or a
    branch. Signalling "leaf" by omission cannot be verified: a host that withheld the
    decomposition for a branch had the stale hash promoted, and the device stored a valid
    hash of a NON-CANONICAL tree over the same leaves. No entry is forged that way -- the
    seal and the keyed path are untouched -- but every later proof from an honest,
    canonically-computing host reconstructs to a different root and is refused, so the
    wallet is stuck. This asserts the device now refuses instead.

    Set up with a real BRANCH sibling, so the omission would genuinely have been wrong.
    """
    store, key = _branch_sibling_case(session)
    honest = ward.store_provider(store)

    def withholds(entry_key: bytes) -> ward.Answer:
        answer = honest(entry_key)
        return answer._replace(
            sibling_split_bit=None, sibling_left=None, sibling_right=None,
            sibling_entry_key=None, sibling_commit=None,
        )

    identifier = next(
        i for i in (b"addr%d" % n for n in range(6))
        if expected_entry_key(_K_PATH, _APP, i) == key
    )
    with pytest.raises(exceptions.TrezorFailure, match="identify the sibling"):
        ward.delete_entry(session, _APP, identifier, withholds)

    # and the entry is still there afterwards -- a refused delete deletes nothing
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, identifier, p))
    assert "entry not found" not in rec.title


@pytest.mark.models("core")
def test_ward_delete_keeps_the_root_canonical_when_a_branch_is_promoted(session: Session):
    """The honest form still works, and leaves the device on the CANONICAL root.

    There is no way to read the device's root, and no need to: the host store rebuilds its
    tree canonically on every query, so a subsequent read succeeding is exactly the
    statement that the root the device derived equals the one a rebuild produces. Promoting
    the stale sibling hash -- what the old code did when the decomposition was withheld --
    diverges at three entries, and every read below would fail.

    Both a read and a WRITE are exercised: an update has to prove the current leaf against
    the device's root, so it fails on a drifted root even if reads somehow did not.
    """
    store, key = _branch_sibling_case(session)
    names = [b"addr%d" % n for n in range(6)]
    identifier = next(i for i in names if expected_entry_key(_K_PATH, _APP, i) == key)

    res, _rec = _write(
        session, store, lambda p: ward.delete_entry(session, _APP, identifier, p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    assert key not in store.blobs
    assert len(store) > 1  # a branch sibling survived, which is the case under test

    remaining = next(i for i in names if expected_entry_key(_K_PATH, _APP, i) in store.blobs)
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, remaining, p))
    assert "entry not found" not in rec.title

    res, _rec = _write(
        session, store,
        lambda p: ward.set_entry(session, _APP, remaining, b"still_writable", p),
        "ward_set_entry",
    )
    ward.apply(store, res)


@pytest.mark.models("core")
def test_ward_deleting_the_last_entry_keeps_verifying(session: Session):
    """Emptying the tree must not turn verification off.

    An empty tree used to be recorded the same way as "this device has never written",
    which is the one state in which nothing is checked -- so a one-entry wallet deleting its
    only entry silently lost rollback and suppression protection, from a state the user has
    every reason to think is protected. Here the host serves back the leaf it held before
    the delete, with a real proof against the pre-delete root, and the device must refuse
    it.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"only_entry")
    stale = WardTrie()
    stale.set(key, store.blobs[key])  # the world as it was one delete ago
    assert stale.root() is not None  # the replay it will attempt is a real, provable tree

    res, _rec = _write(
        session, store, lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    assert len(store) == 0

    with pytest.raises(exceptions.TrezorFailure, match="tree is empty"):
        ward.get_entry(session, _APP, b"addr1", ward.store_provider(stale))


@pytest.mark.models("core")
def test_ward_an_emptied_tree_can_be_written_to_again(session: Session):
    """...and the fix must not brick the wallet it protects.

    There is no leaf left to witness, so an insert here takes the no-proof path exactly as
    on a device that has never written. Without this, refusing everything against an empty
    tree would be a denial of service dressed as a fix.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"only_entry")
    res, _rec = _write(
        session, store, lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    assert len(store) == 0

    _seed(session, store, b"addr2", b"after_the_purge")
    assert len(store) == 1
    _res, rec = _read(session, store, lambda p: ward.get_entry(session, _APP, b"addr2", p))
    assert "after_the_purge" in rec.squashed
