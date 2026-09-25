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

from trezorlib import exceptions
from trezorlib import messages as m
from trezorlib import ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutContent, TrezorTestContext

from ...input_flows import InputFlowConfirmAllWarnings
# The role fixture, and the reject flow it lives beside: the device pins ONE app for WARD, on a held
# confirmation, and none of the tests in this file are about that -- so the role is taken once,
# before each test body, and the sequences below stay about what they were written for. See
# `tests/ward_app.py`.
from ...ward_app import (  # noqa: F401  -- ward_app_pinned is an autouse fixture
    reject_flow,
    reveal_prefix,
    session_switch_prefix,
    ward_app_pinned,
)
from ...ward_keys import derive_k_sig
from ...ward_keys import TAG_REVERT
from ...ward_keys import (
    auth_commit,
    bip39_seed,
    derive_k_auth,
    derive_k_data,
    derive_k_ident,
    derive_k_path,
    derive_ward_id,
)
from ...ward_keys import entry_key as expected_entry_key
from ...ward_keys import (
    open_content,
    open_identity,
    seal_content,
    seal_identity,
    transition_preimage,
    unpack_content,
    unpack_identity,
    TAG_COMMIT,
)
from ...ward_trie import WardTrie, addr_bit
from ...ward_wm import NO_HEAD_NONCE, MockWM

# EVERY TEST HERE SPEAKS THE CONNECT-MODE REQUEST SET -- `WardEntryRequest`, `WardSync`,
# `WardReconcile`, `WardVerifyChain`. Those messages do not exist in a firmware that serves WARD
# over its own channel: the two transports are mutually exclusive by build, with no runtime
# fallback, so on such a build these tests are inapplicable rather than failing.
pytestmark = [pytest.mark.ward, pytest.mark.ward_transport("connect")]

_APP = "TEST"

# The device under test is set up with the default mnemonic and no passphrase
# (`SetupParams` in tests/conftest.py), so the oracle can reproduce its keys.
_MNEMONIC = " ".join(["all"] * 12)
_SEED = bip39_seed(_MNEMONIC)
_K_PATH = derive_k_path(_SEED)
_K_IDENT = derive_k_ident(_SEED)
_K_DATA = derive_k_data(_SEED)
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
        # Set by helpers that also want the ack back, e.g. `_offline_read` -- the screen and the
        # message are two halves of the same answer and asserting one without the other has
        # already let a wrong flag through.
        self.ack = None

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


def _expected(br_name: str, final=m.Success, reveals: type | None = None) -> list:
    """The full PULL round: the device asks for the entry, we answer, then it confirms.

    Pinning the sequence is what proves the pull happened at the protocol level; the
    screen assertions only prove what was rendered. A read ends in Success; a write or
    delete ends in WardLeafAck, because the host needs the leaf the device built.

    A device with no app role asks before it reveals, and that screen comes FIRST -- the check runs
    in the wire filter, so it is answered before the handler pulls anything. See `reveal_prefix`.
    """
    return reveal_prefix(reveals) + [
        m.WardEntryRequest,
        m.ButtonRequest(name=br_name),
        final,
    ]


def _write(
    session: Session, store: WardTrie, call, br_name: str, switched: bool = False
) -> tuple:
    """Run a write/delete, walking its screen, and return (result, recorder).

    `switched` when the caller has been using ANOTHER session since this one last spoke -- see
    `session_switch_prefix`, which is about protocol v1 and not about WARD.
    """
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            (session_switch_prefix() if switched else [])
            + _expected(br_name, m.WardLeafAck)
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        res = call(ward.store_provider(store))
    return res, rec


def _read(session: Session, store: WardTrie, call) -> tuple:
    """Run a read, walking its screen, and return (result, recorder)."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry", reveals=m.WardGetEntry))
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        res = call(ward.store_provider(store))
    return res, rec


def _wm_for(store: WardTrie) -> MockWM:
    """The ONE WM this store's wallet talks to, created on first use.

    WM IDENTITY MATTERS NOW, which it did not before. The device tracks the WM's head nonce
    register and checks each attestation for continuity against the head it last saw, so a
    session that synced against one WM and then against a freshly-built one is refused -- and
    correctly, because that is indistinguishable from a register that was rebuilt behind its
    back. A throwaway WM per round used to be harmless; it is now a WM swap.

    Tests that WANT a different WM say so explicitly, by constructing one -- an impostor with its
    own seed, or a standby in a failover.
    """
    wm = getattr(store, "_wm", None)
    if wm is None:
        wm = MockWM()
        store._wm = wm
    return wm


def _head_init_for(counter: int, root):
    """The opening-head authorisation a connect host relays from `WardSyncAck`.

    A WM with no record of this wallet has nothing to compare against, so the first head it holds
    must be supplied by the device and signed. In production this comes off `WardSyncAck`; here
    the oracle mints it, which is the same statement made by the same key.
    """
    from ...ward_keys import head_init_sig as _oracle_head_init

    return _oracle_head_init(derive_k_sig(_SEED), _WARD_ID, counter, root)


def _nonces(wm: MockWM, ward_id: bytes) -> tuple:
    """The `(consumed, current)` head-nonce pair the WM would attest right now.

    Tests that hand-roll an attestation need BOTH ends: the attested edge is
    `(from_counter, from_root, from_head_nonce) -> (to_counter, to_root, to_head_nonce)`, and the
    device checks the pair for continuity against the head it last saw. Taking them off the WM
    rather than inventing them keeps a synthetic attestation synthetic in exactly the way the test
    means it to be -- a wrong counter, say -- instead of also being incoherent about the nonce and
    failing for a reason the test is not about.
    """
    step = wm.step(ward_id)
    if step is None:
        return NO_HEAD_NONCE, NO_HEAD_NONCE
    return step[5], step[6]


def _publish(wm: MockWM, res, store: WardTrie) -> None:
    """Hand the WM what the write produced, WITH the device's authorisation for it.

    A real host does exactly this: the device is the counter authority, and the WM takes the
    advance only from a party that can prove a holder of this wallet's K_sig authorised it.
    Skipping the publish means the write never takes effect -- the device's head simply does not
    move -- and skipping the SIGNATURE means the WM refuses it outright, which is the property
    `wm_sig` exists for.

    THE AUTHENTICATED PATH, deliberately, because this is where connect-mode `wm_sig` gets
    exercised at all. `MockWM.install_unauthenticated` would also work and would test nothing:
    it is there for fixtures standing in for history, not for a write this test just made.
    """
    # THE WHOLE STEP, not just the head it reaches. Both roots are the host's own -- it derived
    # them by applying the leaf the device handed back -- and the predecessor is what the WM
    # compare-and-swaps on.
    root = store.root()
    from_counter, from_root = _step_into(store, res.counter, root)
    wm.advance(
        _WARD_ID,
        from_counter,
        from_root,
        res.counter,
        root,
        res.wm_sig,
        _T0 + res.counter,
    )


def _go_online(
    session: Session,
    store: WardTrie,
    wm: "MockWM | None" = None,
) -> MockWM:
    """Bring the session out of offline mode by completing one sync round.

    RETURNS THE WM IT USED, whether it was given one or made one. A test that then checks a
    `wm_sig` needs the head nonce that WM holds, because the device quotes it -- so the object has
    to be reachable rather than swallowed here.

    A SESSION STARTS OFFLINE and stays there until a reconcile succeeds -- the device has no
    reason to believe anything it holds is current before then. Offline, `WardGetEntry` and
    `WardSetEntry` REFUSE (the local store has its own requests now), so any test that means to
    exercise the host path has to sync first. A real host does this on connect; the tests simply
    have to say so.

    Adopting the head the host already holds, at the counter it already has, so this changes
    no state -- it only tells the device that what it has is confirmed.
    """
    wm = wm or _wm_for(store)
    _attest(session, wm, store)
    return wm


def _seed(
    session: Session,
    store: WardTrie,
    identifier: bytes,
    value: bytes,
) -> bytes:
    """Create an entry the only way a host can: ask the device to build the leaf.

    The host cannot synthesise one -- that is the point of the device being the encoder --
    so every fixture below goes through a real confirmed write.

    The write alone does not move the device's head: since commit-on-WM-confirmation, only
    an attestation does. So seeding an entry means sync, write, apply, and then run the round
    again -- which is what a real host does too, and why it is folded in here rather than
    repeated at eighty call sites.

    The LEADING round is what makes the write possible at all: offline, `WardSetEntry` refuses,
    because with no host to pull from there is no current state to derive a root against. Holding
    the change instead is `WardQueueSetEntry`, a different request with a different ack.
    """
    _go_online(session, store)
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, identifier, value, p),
        "ward_set_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)
    return res.entry_key


def _confirm(
    session: Session,
    store: WardTrie,
    wm: "MockWM | None" = None,
) -> None:
    """Run the WM round that makes the device adopt the head the host now holds.

    The store's own WM is used unless the test names one -- see `_wm_for`. It is no longer a
    throwaway: the device checks each attestation's head nonce for continuity against the head it
    last saw, so a fresh WM per round would read as a register rebuilt behind the session's back.
    """
    wm = wm or _wm_for(store)
    _attest(session, wm, store)
    return wm


# --- the keyed path --------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_pull_names_only_the_opaque_key(session: Session):
    """The request must carry a 32-byte key and NOTHING that reveals the entry."""
    _go_online(session, WardTrie())
    identifier = b"addr1"
    asked: list[bytes] = []

    def provider(entry_key: bytes):
        asked.append(entry_key)
        return ward.Answer()

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_get_entry", reveals=m.WardGetEntry))
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
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
    _go_online(session, WardTrie())
    res, _rec = _read(
        session, WardTrie(), lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr1")


@pytest.mark.models("core")
def test_ward_pull_key_is_deterministic_and_domain_separated(session: Session):
    """Same (app_id, identifier) -> same key; different app_id -> different key.

    Determinism is what makes the store usable at all; domain separation is what stops
    one app's entry from resolving another's. Both are observable from the host side
    without any knowledge of the seed.
    """
    _go_online(session, WardTrie())
    keys = [
        _read(
            session,
            WardTrie(),
            lambda p, a=app: ward.get_entry(session, a, b"addr1", p),
        )[0].entry_key
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
    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )
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
    _confirm(session, store)
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
    store.set(
        key,
        ward.Leaf(
            store.blobs[key].identity,
            m.WardLeafContent(
                encoding=0,
                encrypted=m.WardEncryptedLeaf(
                    nonce=sealed.nonce, tag=sealed.tag, ct=flipped
                ),
            ),
        ),
    )

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

    res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )

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
    _go_online(session, WardTrie())
    _res, rec = _read(
        session, WardTrie(), lambda p: ward.get_entry(session, _APP, b"nope", p)
    )

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

    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )

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

    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr2", p)
    )

    assert "two" in rec.text
    assert "one" not in rec.text


# --- add / update -----------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_set_entry_add_shows_the_new_value(session: Session):
    """Writing a key the host does not hold is an ADD: nothing is being replaced, so the
    screen must not claim otherwise."""
    store = WardTrie()
    _go_online(session, store)

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
    _confirm(session, store)
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
    _confirm(session, store)
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
    _confirm(session, store)
    assert list(store.blobs) == [keep]


@pytest.mark.models("core")
def test_ward_delete_entry_is_idempotent_on_a_proved_absence(session: Session):
    """Deleting a path that already holds nothing succeeds, and changes nothing.

    The absence is PROVED before this decides anything -- the pull demands a
    non-membership witness against the trusted root -- so the device is not taking the
    host's word for it. That is what makes idempotence safe here rather than lax.

    No screen: a hold-to-confirm that always means "nothing happened" is one that gets
    approved without being read. Hence no input flow, and WardLeafAck arrives with no
    ButtonRequest before it.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"keep_me")  # so absence needs a real witness
    before = store.counter

    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.WardEntryRequest, m.WardLeafAck])
        res = ward.delete_entry(session, _APP, b"ghost", ward.store_provider(store))

    # the same empty leaf a real delete returns, so a host applies both the same way
    assert res.leaf is not None
    assert res.leaf.content.plaintext.content == b""
    # ...but nothing moved: no transition happened, so none was authorised
    assert res.auth_commit is None
    assert res.counter == before

    ward.apply(store, res)
    _confirm(session, store)
    assert list(store.blobs) == [expected_entry_key(_K_PATH, _APP, b"addr1")]
    assert store.counter == before


@pytest.mark.models("core")
def test_ward_delete_entry_retry_after_a_lost_response_succeeds(session: Session):
    """A lost response is now a no-op rather than a stuck state.

    The device did not commit, so the delete never happened and the retry is an ordinary
    fresh attempt against unchanged state. Under commit-on-write the device HAD advanced
    while the host had not, so the retry served a proof against a root the device had moved
    past and was refused with nothing to say why -- which is what idempotent delete and the
    sync counter were both introduced to soften.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"doomed")
    keep = _seed(session, store, b"addr2", b"keep_me")
    before = ward.sync(session).counter

    _res, _rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    assert ward.sync(session).counter == before  # the ack was lost; nothing landed

    res2, _rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    ward.apply(store, res2)
    _confirm(session, store)
    assert list(store.blobs) == [keep]


@pytest.mark.models("core")
def test_ward_delete_entry_still_refuses_an_unproved_absence(session: Session):
    """Idempotence rests on the proof, so an unwitnessed denial is still refused.

    Without this, "delete succeeds when the host says the entry is gone" would let a host
    suppress an entry and have the device agree it never existed.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"present")

    def denies_everything(_entry_key: bytes) -> ward.Answer:
        return ward.Answer()

    with pytest.raises(exceptions.TrezorFailure, match="witness"):
        ward.delete_entry(session, _APP, b"addr1", denies_everything)


@pytest.mark.models("core")
def test_ward_apply_refuses_to_drop_a_no_change_result_on_a_live_entry(
    session: Session,
):
    """Host-side guard: "nothing changed" must not be applied over an entry that exists.

    If the device reports no transition while the store still holds the entry, the two
    disagree about the world. Silently carrying on leaves a row the device believes is
    gone, and every later proof for it is refused with nothing to say why.
    """
    store = WardTrie()
    key = _seed(session, store, b"addr1", b"present")

    with session.test_ctx as ctx:
        ctx.set_expected_responses([m.WardEntryRequest, m.WardLeafAck])
        res = ward.delete_entry(session, _APP, b"ghost", ward.store_provider(store))

    # pretend the no-change result was for the live entry -- the shape a confused host
    # would produce
    with pytest.raises(ValueError, match="disagree about the current state"):
        ward.apply(store, res._replace(entry_key=key))


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
    _confirm(session, store)
    assert len(store) == 0


# --- shared validation ------------------------------------------------------------


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda s: ward.get_entry(s, _APP, b"", lambda _k: ward.Answer()), id="get"
        ),
        pytest.param(
            lambda s: ward.set_entry(s, _APP, b"", b"v", lambda _k: ward.Answer()),
            id="set",
        ),
        pytest.param(
            lambda s: ward.delete_entry(s, _APP, b"", lambda _k: ward.Answer()),
            id="delete",
        ),
        pytest.param(
            lambda s: ward.get_entry(s, "", b"addr1", lambda _k: ward.Answer()),
            id="get-no-app",
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
    _confirm(session, store)

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
    _go_online(fresh, store)
    _res, rec = _read(fresh, store, lambda p: ward.get_entry(fresh, _APP, b"addr1", p))
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
        # `fresh` has been speaking since this session last did; on v1 coming back costs an
        # Initialize round trip.
        switched=True,
    )
    ward.apply(store, res)
    _confirm(session, store)

    # Sync first: a session that has not is served from the device's own store, and would
    # never ask the host for this leaf at all -- so there would be nothing to refuse.
    another = session.test_ctx.get_session()
    _go_online(another, store)
    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(another, _APP, b"addr1", ward.store_provider(stale))


@pytest.mark.models("core")
@pytest.mark.setup_client(passphrase=True)
def test_ward_is_isolated_per_hidden_wallet(test_ctx: TrezorTestContext):
    """Two hidden wallets share a device and share nothing else.

    Everything WARD holds hangs off the passphrase-dependent seed: K_path, so the same
    (app_id, identifier) lands on a DIFFERENT path; and the stored root and counter, which
    `storage.ward` keys by a wallet_id derived from that seed. Until now that isolation was
    asserted only at the storage level, where a slot-keying bug is visible but a derivation
    one is not -- a device that derived every wallet's K_path from a passphrase-free seed
    would pass those tests and silently put two wallets' entries at one path.

    Asserted three ways, because each catches a different failure:
      the paths differ, and each matches what the oracle derives for THAT passphrase --
        so the device really is deriving per wallet, not merely inconsistently;
      one wallet's leaf is refused by the other, since their roots are independent;
      the counters advance independently.
    """
    alpha = test_ctx.get_session(passphrase="alpha")
    beta = test_ctx.get_session(passphrase="beta")

    _SEED_ALPHA = bip39_seed(_MNEMONIC, "alpha")
    _SEED_BETA = bip39_seed(_MNEMONIC, "beta")
    k_alpha = derive_k_path(_SEED_ALPHA)
    k_beta = derive_k_path(_SEED_BETA)
    assert k_alpha != k_beta  # the oracle's own premise, cheap to state

    store_a, store_b = WardTrie(), WardTrie()
    key_a = _seed(
        alpha, store_a, b"addr1", b"alpha_value"
    )
    key_b = _seed(
        beta, store_b, b"addr1", b"beta_value"
    )

    # SAME app_id and identifier, different paths -- and each is the right one
    assert key_a == expected_entry_key(k_alpha, _APP, b"addr1")
    assert key_b == expected_entry_key(k_beta, _APP, b"addr1")
    assert key_a != key_b

    # ...so neither wallet can be served the other's leaf. Both have written by now, so both
    # hold a root: without that, "no root" would mean "verify nothing" and this would pass
    # for the wrong reason.
    with pytest.raises(exceptions.TrezorFailure, match="trusted root"):
        ward.get_entry(alpha, _APP, b"addr1", ward.store_provider(store_b))

    # and the counters are each wallet's own
    _seed(alpha, store_a, b"addr2", b"more")
    _seed(alpha, store_a, b"addr3", b"more")
    assert ward.sync(alpha).counter == store_a.counter
    assert ward.sync(beta).counter == store_b.counter
    assert store_a.counter > store_b.counter  # 3 writes vs 1


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
    # THE TRANSITION LOG AND THE ARCHIVE COME ALONG, because a subset is still the same HOST
    # holding the same history -- only its view of the tree differs. Leaving them behind was
    # invisible while a sync round needed nothing but a root; now `_attest` folds the link into
    # the head it adopts, so a subset without `links` cannot complete one and fails inside the
    # helper rather than at the device.
    out.links = list(store.links)
    # NOTE: a subset holding every leaf of its source has the SAME root. Where a test
    # needs a genuinely different tree, assert that -- otherwise it can silently become a
    # test of the identical tree, which passes for the wrong reason.
    return out


def _step_into(store: WardTrie, to_counter: int, to_root, links=()):
    """The step a WM would attest for `(to_counter, to_root)` -- its `from` end.

    Taken from the transition log, which is where a real WM's predecessor comes from too: it
    compare-and-swapped on that end before installing this head.

    `links` is searched FIRST, for the catch-up tests that mint a history "made elsewhere while
    this device was away". Those steps never entered this host's own log, but they are the real
    ones -- and since the device now checks that the walk's first link begins where the
    attestation said it did, naming anything else would make the fixture, not the firmware, the
    thing under test.

    A SYNTHETIC head -- a counter no transition produced, which a few tests attest deliberately to
    reach the device's counter rules -- has no entry anywhere, so it falls back to naming the
    state one counter back. That satisfies contiguity without claiming a link exists.

    Genesis attests itself: counter 0 had no predecessor.
    """
    if to_counter == 0:
        return 0, to_root
    for fc, fr, tc, tr, _ac in list(links) + list(store.links):
        if tc == to_counter and (tr or None) == (to_root or None):
            return fc, fr
    return to_counter - 1, None


def _link_into(store: WardTrie, to_counter: int):
    """The transition log entry that PRODUCED the state at `to_counter`, or None at genesis.

    Note it is the link INTO the target, not the one out of it: the device authorises the
    target by the transition that created it, which is what lets a caller jump back past
    steps whose own links it never received.

    NONE AT COUNTER 0. The tree is empty there and no transition made it, so there is nothing to
    authorise -- which `reconcile` requires rather than merely tolerates, since a link claiming
    to produce counter 0 would be describing a transition that cannot exist.
    """
    if to_counter == 0:
        return None
    # NEWEST FIRST. A counter can be produced TWICE once a demotion exists: the original write
    # reached it, and a recovery minted a REVERT that reaches it again carrying an older root.
    # The later one is the live history, so scanning forward would hand back a link into a head
    # the wallet has moved off -- authentic, and not the one the WM attested.
    for link in reversed(store.links):
        if link[2] == to_counter:
            return link
    raise AssertionError("no link produces counter %d" % to_counter)


_DERIVE_LINK = object()


def _attest(
    session: Session,
    wm: MockWM,
    store: WardTrie,
    counter: int | None = None,
    timestamp: int | None = None,
    link=_DERIVE_LINK,
) -> None:
    """Run a full sync round: nonce, WM attestation, the link into the head.

    THE WM IS TOLD THE ROOT. It holds `(counter, root)` in the clear, so nothing here needs a key
    of the wallet's -- which is why the `k_mac` this helper used to thread through every fixture
    is gone. What the device will not take on the WM's word is that the state is REAL, so the
    reconcile below also hands it the authorised link into that head.

    `link` OVERRIDES the one taken from the host's log, and exists for the tests that attest a
    SYNTHETIC head -- a counter no transition ever produced, used to reach the device's counter
    rules. The host's log cannot hold a link into a state that never happened, so those tests mint
    one with `_link`, which they can do because the oracle holds K_auth. Pass nothing and the real
    link is used, which is what every ordinary fixture wants.
    """
    if counter is None:
        counter = store.counter
    if timestamp is None:
        timestamp = (
            _T0 + counter
        )  # time moves with the counter, as it would in practice
    ack = ward.sync(session)
    # ward_id comes from the DEVICE, since it is passphrase-dependent and this helper is used by
    # more than the default wallet. The root is the host's own -- no wallet key involved.
    root = store.root()
    # THE STEP THE WM ATTESTS, not the head alone. Taken from the link being presented below, so
    # the two descriptions of this transition agree -- which is the whole point of the attestation
    # naming one. `link` overrides it for the synthetic-head tests, which have no real link.
    into = _link_into(store, counter) if link is _DERIVE_LINK else link
    from_counter, from_root = (into[0], into[1]) if into is not None else (0, None)
    wm.install_unauthenticated(ack.ward_id, counter, root, timestamp, from_counter, from_root)
    _fc, _fr, from_head_nonce, _c, _m, head_nonce, _t, sig = wm.attest(ack.ward_id, ack.nonce)
    # THE WM'S HEAD NONCE travels back with the attestation and is covered by it, so the device
    # learns it from a signed statement rather than from the host. It is what the device's next
    # `wm_sig` will quote.
    ward.ingest_attestation(
        session,
        from_counter,
        from_root,
        counter,
        root,
        sig,
        from_head_nonce,
        head_nonce,
        timestamp,
    )
    # THE LINK INTO THE HEAD, which reconcile now requires: an attestation says the WM calls this
    # head current, and only the link says a device of this wallet ever produced it. None at
    # counter 0, where the tree is empty and no transition made it.
    ward.reconcile(session, into)
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

    wm = _wm_for(store)
    # A MINTED LINK, because no real one exists: this head is synthetic -- nobody ever wrote the
    # transition that would have produced it. The oracle holds K_auth, so it can authorise one,
    # which is exactly what a second device of this wallet would have done.
    _attest(
        session,
        wm,
        foreign,
        counter=store.counter + 1,
        link=_link(store.counter, store.root(), store.counter + 1, foreign.root()),
    )

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
    root = store.root()
    # Any head nonce will do: the signer is wrong, so this is refused before the nonce it names
    # can matter. Naming one the device would accept is the point -- nothing else about the
    # message is malformed.
    from_head_nonce = bytes([0x2A]) * 32
    head_nonce = bytes([0x3B]) * 32
    sig = impostor.sign(ack.ward_id, ack.nonce, *_step_into(store, counter, root), from_head_nonce, counter, root, head_nonce, _T0 + counter)

    with pytest.raises(
        exceptions.TrezorFailure, match="attestation verification failed"
    ):
        ward.ingest_attestation(session, *_step_into(store, counter, root), counter, root, sig, from_head_nonce, head_nonce, _T0 + counter)


@pytest.mark.models("core")
def test_ward_refuses_an_attestation_bound_to_another_nonce(session: Session):
    """A stockpiled anchor is useless: the signature is bound to a nonce the device minted
    for THIS round, which the WM could not have known in advance.

    Without this a host could collect signed anchors while the network was in a state it
    liked and serve one whenever it suited.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)

    # an anchor signed against an earlier round's nonce
    counter = store.counter
    stale_ack = ward.sync(session)
    root = store.root()
    stale_sig = wm.sign(stale_ack.ward_id, stale_ack.nonce, *_step_into(store, counter, root), _nonces(wm, stale_ack.ward_id)[0], counter, root, wm.head_nonce(stale_ack.ward_id), _T0 + counter)

    ward.sync(session)  # a new round, a new nonce
    with pytest.raises(
        exceptions.TrezorFailure, match="attestation verification failed"
    ):
        ward.ingest_attestation(session, *_step_into(store, counter, root), counter, root, stale_sig, _nonces(wm, stale_ack.ward_id)[0], wm.head_nonce(stale_ack.ward_id), _T0 + counter)


@pytest.mark.models("core")
def test_ward_refuses_a_link_into_a_head_the_wm_did_not_attest(session: Session):
    """The LINK is what binds the WM's claim to actual contents.

    The attestation here is genuine and current, and it names the real root -- the WM signs
    `(counter, root)` in the clear now, so there is no root for the host to substitute on the
    wire. What a host CAN still try is to present the link into a different head, and that is
    what fails: `auth_commit` needs K_auth, which never leaves the device.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    other_key = _seed(session, store, b"addr2", b"w")
    other = _subset(store, [other_key])  # a different root; reconcile fails on the link

    wm = _wm_for(store)
    counter = store.counter
    ack = ward.sync(session)
    # ward_id comes from the DEVICE, being passphrase-dependent. The root is the host's own.
    root = store.root()
    wm.install_unauthenticated(ack.ward_id, counter, root, _T0 + counter, *_step_into(store, counter, root))
    _fc, _fr, _fhn, _c, _m, _hn, _t, sig = wm.attest(ack.ward_id, ack.nonce)
    ward.ingest_attestation(session, *_step_into(store, counter, root), counter, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + counter)

    # A LINK AUTHORISED FOR A DIFFERENT DESTINATION. Rewriting the `to_root` of a genuine link
    # would prove nothing -- `WardReconcile` does not carry that field, so the edit never reaches
    # the wire and the device recomputes over the attested root regardless. So the oracle mints a
    # real `auth_commit` ending at `other`, which is the strongest thing a host could hold, and
    # the device still refuses: what it recomputes is the transition into the head the WM named.
    bogus = _link(counter - 1, store.root(), counter, other.root())
    with pytest.raises(exceptions.TrezorFailure, match="is not authorised"):
        ward.reconcile(session, bogus)


@pytest.mark.models("core")
def test_ward_refuses_an_attested_counter_below_the_floor(session: Session):
    """Anti-rollback. The floor is what stops a WM replaying an old head and freezing the
    device there -- and since the WM now attests roots in the clear, it is the ONLY bound left
    on a WM that lies about which state is current."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)

    # RAISED ONE STEP AT A TIME, because reconcile adopts at most one. It used to accept the
    # whole jump in a single round, which is exactly the finding that closed: a device cannot be
    # carried across counters it has no predecessor for. Each step keeps the same root, so only
    # the counter moves -- all this test needs is a floor well above where it will aim next.
    for _ in range(5):
        at = store.counter + 1
        _attest(
            session,
            wm,
            store,
            counter=at,
            link=_link(at - 1, store.root(), at, store.root()),
        )

    behind = store.counter - 1
    ack = ward.sync(session)
    old_root = store.root()
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, behind, old_root), _nonces(wm, ack.ward_id)[0], behind, old_root, wm.head_nonce(ack.ward_id), _T0 + behind)
    with pytest.raises(exceptions.TrezorFailure, match="older than the stored counter"):
        ward.ingest_attestation(session, *_step_into(store, behind, old_root), behind, old_root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + behind)


@pytest.mark.models("core")
def test_ward_reconcile_refuses_a_multi_step_jump(session: Session):
    """RECONCILE ADOPTS AT MOST ONE STEP, and names the route that adopts more.

    It used to take any attested counter at or above the stored one while verifying a single
    transition -- so a device at 10 could be moved to 40 on the strength of one link, with
    11..39 taken on the WM's word alone. That made the WM an authority on LINEAGE, which it is
    not: an attestation establishes freshness and ordering, and DESCENT establishes state.

    Everything here is cryptographically genuine -- the attestation verifies, the link verifies,
    both under the real keys. What is refused is the GAP between them and this device's head.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)

    target = store.counter + 2
    root = store.root()
    ack = ward.sync(session)
    # A genuine attested step, two counters ahead: contiguous with ITSELF, which is all the
    # attestation check asks, and disconnected from where this device stands, which is what the
    # handler now asks as well.
    sig = wm.sign(
        ack.ward_id, ack.nonce, target - 1, root, _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target
    )
    ward.ingest_attestation(
        session, target - 1, root, target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target
    )

    with pytest.raises(exceptions.TrezorFailure, match="use WardVerifyChain"):
        ward.reconcile(session, _link(target - 1, root, target, root))


@pytest.mark.models("core")
def test_ward_reconcile_refuses_a_step_from_elsewhere(session: Session):
    """ONE STEP IS NOT ENOUGH; it has to be one step FROM HERE.

    The counter advances by exactly one and the link is genuine -- but the predecessor the WM
    attested is not the head this device holds. Accepting it would mean adopting a state whose
    parent this device has never been at, which is a one-counter fork rather than a catch-up.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    other_key = _seed(session, store, b"addr2", b"w")
    elsewhere = _subset(store, [other_key])
    assert elsewhere.root() != store.root()

    wm = _wm_for(store)
    target = store.counter + 1
    root = store.root()
    ack = ward.sync(session)
    sig = wm.sign(
        ack.ward_id, ack.nonce, target - 1, elsewhere.root(), _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target
    )
    ward.ingest_attestation(
        session, target - 1, elsewhere.root(), target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target
    )

    with pytest.raises(
        exceptions.TrezorFailure, match="does not start at this device's head"
    ):
        ward.reconcile(
            session, _link(target - 1, elsewhere.root(), target, root)
        )


@pytest.mark.models("core")
def test_ward_reconcile_refuses_a_lower_counter_outside_recovery(session: Session):
    """A DEMOTION NEEDS THE USER, and the round is where that consent is recorded.

    A demotion refuses to run without the user's hold, and records consent for one counter before
    marking the round. Reaching an attested round any other way and then naming a lower counter
    must not inherit that exemption -- and cannot, because the exemption lives in the round's
    state rather than being inferred from the shape of the counters.

    The floor in `ingest` is what refuses it here; this test pins that the two rules together
    leave no way to lower the head without the screen.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")
    wm = _wm_for(store)

    behind = store.counter - 1
    root = store.root()
    ack = ward.sync(session)
    sig = wm.sign(
        ack.ward_id, ack.nonce, behind - 1, root, _nonces(wm, ack.ward_id)[0], behind, root, wm.head_nonce(ack.ward_id), _T0 + behind
    )
    with pytest.raises(exceptions.TrezorFailure, match="older than the stored counter"):
        ward.ingest_attestation(
            session, behind - 1, root, behind, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + behind
        )


@pytest.mark.models("core")
def test_ward_a_write_authorises_its_advance_to_the_wm(session: Session):
    """CONNECT-MODE WRITES CARRY `wm_sig`, which is what lets a WM refuse an unauthorised advance.

    Without it the WM has nothing to check when a host publishes `(counter, root)`, so whoever
    knows `ward_id` can advance the counter and have every genuine device refused from then on --
    the WM becomes a denial-of-service oracle. The service channel carried this from the start;
    connect, the transport that is actually developed, did not.

    Pinned against the ORACLE, which implements the preimage independently: a device that signed
    different bytes would be caught here rather than at a WM that cannot tell us why.
    """
    from ...ward_keys import TAG_WM_REVERT, verify_wm_sig

    store = WardTrie()
    wm = _go_online(session, store)
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"v", p),
        "ward_set_entry",
    )

    assert res.wm_sig is not None
    assert len(res.wm_sig) == 64

    from_root = None  # the first write starts from an empty tree
    ward.apply(store, res)

    # THE NONCE THE DEVICE QUOTED, which it can only have learned from the attestation the sync
    # round just verified. Checking against the WM's own value is the whole point: it is what the
    # WM will compare on, and a device signing against anything else produces an authorisation
    # that verifies nowhere.
    head_nonce = wm.head_nonce(_WARD_ID)

    # It verifies against `ward_id` -- which IS the public half of K_sig, so a WM needs no
    # enrolment and no second per-wallet value -- over exactly the transition that happened.
    assert verify_wm_sig(
        _WARD_ID,
        res.counter - 1,
        from_root,
        res.counter,
        store.root(),
        head_nonce,
        res.wm_sig,
    )
    # ...and only under the ORDINARY tag. A write is not a demotion, and a WM that could not
    # tell them apart could not apply policy to one.
    assert not verify_wm_sig(
        _WARD_ID,
        res.counter - 1,
        from_root,
        res.counter,
        store.root(),
        head_nonce,
        res.wm_sig,
        TAG_WM_REVERT,
    )
    # ...and NOT under any other moment in the WM's history. The endpoints are the same; the
    # nonce is not, which is what stops a kept authorisation landing a second time.
    assert not verify_wm_sig(
        _WARD_ID,
        res.counter - 1,
        from_root,
        res.counter,
        store.root(),
        bytes([0xEE]) * 32,
        res.wm_sig,
    )


@pytest.mark.models("core")
def test_ward_the_wm_refuses_an_unauthorised_advance(session: Session):
    """The other half of the same property, asserted where it bites: at the WM.

    A host that publishes without the device's signature, or with one minted by another key, is
    refused. This is the denial of service `wm_sig` closes, demonstrated rather than described.
    """
    store = WardTrie()
    _go_online(session, store)
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr2", b"v", p),
        "ward_set_entry",
    )
    ward.apply(store, res)

    # THE WM MUST ALREADY KNOW THE WALLET, because an advance cannot enrol: an authorisation has
    # to quote the nonce the WM holds, and one that has never seen this wallet holds none.
    # Enrolment is a sync-path operation. Here a fixture stands in for the history that put this
    # head there.
    wm = _wm_for(store)
    from_counter, from_root = _step_into(store, res.counter, store.root())
    wm.install_unauthenticated(
        _WARD_ID, from_counter, from_root, _T0 + from_counter
    )

    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(
            _WARD_ID,
            from_counter,
            from_root,
            res.counter,
            store.root(),
            bytes(64),  # no signature at all
            _T0 + res.counter,
        )

    # ...and one from a wallet that is not this one is no better.
    other = _link(from_counter, from_root, res.counter, store.root())
    assert other  # the oracle's K_auth MAC, not an Ed25519 signature over this transition
    with pytest.raises(ValueError, match="not authorised"):
        wm.advance(
            _WARD_ID,
            from_counter,
            from_root,
            res.counter,
            store.root(),
            other[4] + other[4],  # 64 bytes of the wrong thing
            _T0 + res.counter,
        )


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
    wm = _wm_for(store)
    _attest(session, wm, store)  # the device's real state, at its own counter

    # a DIFFERENT state offered at that same counter
    divergent = _subset(store, [other_key])
    counter = store.counter

    ack = ward.sync(session)
    root = divergent.root()
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, counter, root), _nonces(wm, ack.ward_id)[0], counter, root, wm.head_nonce(ack.ward_id), _T0 + counter)
    ward.ingest_attestation(session, *_step_into(store, counter, root), counter, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + counter)
    # THE LINK IS GENUINE, and minted over EXACTLY the step the attestation names -- the same
    # `_step_into` both sides use -- so `verify_inbound_link` passes. What refuses this is the
    # SECOND gate: the device already stands at this counter holding a different root, and one
    # counter names one state. Both gates are real; this test is about that one.
    fc, fr = _step_into(store, counter, root)
    with pytest.raises(
        exceptions.TrezorFailure, match="attested counter matches but the root differs"
    ):
        ward.reconcile(session, _link(fc, fr, counter, root))


@pytest.mark.models("core")
def test_ward_reconcile_needs_an_attestation_first(session: Session):
    """A root on its own adopts nothing -- otherwise the host could simply announce one."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")

    ward.sync(session)  # round open, nothing attested
    with pytest.raises(exceptions.TrezorFailure, match="no attested sync round"):
        ward.reconcile(session, _link_into(store, store.counter))


@pytest.mark.models("core")
def test_ward_an_attestation_cannot_be_adopted_twice(session: Session):
    """The round closes on adoption, so a replayed reconcile has nothing to act on."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)
    _attest(session, wm, store)

    with pytest.raises(exceptions.TrezorFailure, match="no attested sync round"):
        ward.reconcile(session, _link_into(store, store.counter))


# --- writes advance the counter -----------------------------------------------------


@pytest.mark.models("core")
def test_ward_a_write_does_not_move_the_head_until_confirmed(session: Session):
    """THE invariant of commit-on-WM-confirmation, asserted directly.

    A write hands back the counter and mac the host must publish, but the device itself does
    not take them. Its head moves only when a WM attestation names that counter and a mac it
    can reproduce. That is what makes two devices unable to hold the same unconfirmed
    counter -- neither holds one at all -- and it is what lets the stored head be treated as
    always-confirmed.
    """
    store = WardTrie()
    _go_online(session, store)
    before = ward.sync(session).counter

    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"one", p),
        "ward_set_entry",
    )
    assert res.counter == before + 1  # the ack names the next counter...
    assert ward.sync(session).counter == before  # ...and the device has NOT taken it

    ward.apply(store, res)
    _confirm(session, store)
    assert ward.sync(session).counter == res.counter  # only now


@pytest.mark.models("core")
def test_ward_a_published_write_syncs_cleanly(session: Session):
    """Publish what the write produced and the next sync is a no-op, not a conflict.

    Same counter, same root -- so the device accepts, and nothing is discarded. This is
    the round trip that closes the window the previous step had to document.
    """
    store = WardTrie()
    _go_online(session, store)
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"kept", p),
        "ward_set_entry",
    )
    ward.apply(store, res)

    # PUBLISHED, not installed by fiat, and that ordering matters now that one WM serves the
    # whole wallet: `_confirm` would put the head there itself, leaving this authenticated
    # advance nothing to move and turning the round trip under test into a conflict.
    wm = _wm_for(store)
    _publish(wm, res, store)

    ack = ward.sync(session)
    # RELAYED, not recomputed: the host forwards the step the WM signed. Deriving it again here
    # would be the fixture agreeing with itself, and would break the moment the two disagreed.
    fc, fr, fhn, counter, root, hn, ts, sig = wm.attest(ack.ward_id, ack.nonce)
    ward.ingest_attestation(session, fc, fr, counter, root, sig, fhn, hn, ts)
    ward.reconcile(session, _link_into(store, counter))
    store.counter = counter  # device and store now agree

    # the entry survived the round trip
    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )
    assert "kept" in rec.text


@pytest.mark.models("core")
def test_ward_an_unpublished_write_simply_does_not_happen(session: Session):
    """A write the host never publishes leaves no trace, instead of wedging the wallet.

    This replaces a test of the opposite behaviour. Under commit-on-write the device advanced
    locally, so an unpublished write put it AHEAD of the WM, every sync was refused as a
    rollback, and the only ways out were publishing the pair or reverting. There is now
    nothing to be ahead of, so the failure mode is gone rather than handled.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"kept")
    before = ward.sync(session).counter

    _res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr2", b"unpublished", p),
        "ward_set_entry",
    )
    # neither applied nor confirmed: the host drops it on the floor
    assert ward.sync(session).counter == before

    # and the wallet still works -- no stuck state to escape from
    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr1", p)
    )
    assert "kept" in rec.squashed


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
        auth_commit(
            _K_AUTH, _WARD_ID, from_counter, from_root, to_counter, to_root
        ),
    )


def _revert_link(from_counter, from_root, to_counter, to_root):
    """A DEMOTION minted by "another device of this wallet".

    The counter still moves FORWARD -- `rollback` emits (c, head) -> (c+1, an older root), so a
    revert is a real transition and the history containing it stays walkable. What makes it a
    revert is the tag, which is the only thing telling the WM (and a catching-up device) that the
    state it carries is being restored rather than written.
    """
    return (
        from_counter,
        from_root,
        to_counter,
        to_root,
        auth_commit(
            _K_AUTH,
            _WARD_ID,
            from_counter,
            from_root,
            to_counter,
            to_root,
            TAG_REVERT,
        ),
    )


def _serves(links):
    """A `link_source` for `ward.verify_chain` backed by a fixed list of links.

    The device walks BACKWARDS from the anchored head, asking for the link that ends at a
    specific (counter, root) -- so this answers by the `to` end, newest first, exactly as a host
    indexing its transition log would. A real host uses `WardTrie.links_ending_at`; these tests
    build their links by hand, so they need the same lookup over a plain list.
    """

    def source(to_counter, to_root, limit):
        out = []
        counter, root = to_counter, to_root
        while len(out) < limit:
            for link in links:
                fc, fr, tc, tr, _ac = link
                if tc == counter and (tr or None) == (root or None):
                    out.append(link)
                    counter, root = fc, fr
                    break
            else:
                break
        return out

    return source


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

    wm = _wm_for(store)
    ack = ward.sync(session)
    root = head.root()
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, target, root, links), _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target)
    ward.ingest_attestation(session, *_step_into(store, target, root, links), target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target)
    res = ward.verify_chain(session, _serves(links))

    assert res.counter == target
    assert res.new_root == head.root()

    # the adopted tree is the one it now verifies against
    head.counter = target
    _res, rec = _read(session, head, lambda p: ward.get_entry(session, _APP, b"b", p))
    assert "two" in rec.text


@pytest.mark.models("core")
def test_ward_catches_up_further_than_one_ack_can_carry(session: Session):
    """THE REASON THE WALK IS A PULL, and the case the old forward push could not express.

    Links used to travel as one unchunked repeated field in an 8704-byte buffer -- about 77 of
    them -- so a device further behind than that could not catch up in a single message at all,
    and the workaround was to persist intermediate heads proved by archived attestations. Pulling
    them instead moves that ceiling from the WALK to one ACK: the device asks again, and again,
    and nothing is persisted until it arrives.

    `max_links_per_ack=2` here stands in for the buffer. Five transitions therefore take three
    round trips, and the call count is asserted rather than assumed -- a walk that silently fitted
    everything into one ack would pass every other assertion in this test.
    """
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    k2 = _seed(session, store, b"b", b"two")
    k3 = _seed(session, store, b"c", b"three")
    base_counter, base_root = store.counter, store.root()

    # five transitions made elsewhere while this device was away; distinct leaf sets, so
    # distinct roots -- a repeat would let a step be satisfied by the wrong link
    states = [
        _subset(store, [k1]),
        _subset(store, [k1, k2]),
        _subset(store, [k2, k3]),
        _subset(store, [k1, k2, k3]),
        _subset(store, [k3]),
    ]
    assert len({st.root() for st in states}) == len(states)

    links = []
    counter, root = base_counter, base_root
    for st in states:
        links.append(_link(counter, root, counter + 1, st.root()))
        counter, root = counter + 1, st.root()
    head, target = states[-1], counter

    wm = _wm_for(store)
    ack = ward.sync(session)
    root = head.root()
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, target, root, links), _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target)
    ward.ingest_attestation(session, *_step_into(store, target, root, links), target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target)

    asked = []
    serve = _serves(links)

    def counting(to_counter, to_root, limit):
        asked.append(to_counter)
        return serve(to_counter, to_root, limit)

    res = ward.verify_chain(session, counting, max_links_per_ack=2)

    assert res.counter == target
    assert res.new_root == head.root()
    # THE PULL ACTUALLY LOOPED: three acks for five links, each request naming the state whose
    # predecessor it wants -- walking DOWN from the anchored head, not up from our own.
    assert asked == [target, target - 2, target - 4]

    # ...and the tree it adopted is the one it now verifies reads against
    head.counter = target
    _res, rec = _read(session, head, lambda p: ward.get_entry(session, _APP, b"c", p))
    assert "three" in rec.text


@pytest.mark.models("core")
def test_ward_catches_up_across_a_revert_to_a_state_below_its_own_head(session: Session):
    """The walk crosses a DEMOTION, and the state it restores is one from below this device.

    Another device rolled the wallet back while this one was away. The counter still moved
    forward -- `rollback` emits (c, head) -> (c+1, an older root) -- so the history is walkable
    and the backward chain reaches this device's head exactly as it would across ordinary writes.
    What comes out the far end is a HIGHER counter carrying an OLDER tree: the adopted root here
    is the one the wallet had before this device's own last write.

    That combination is what makes a revert different from everything else the walk can cross. An
    ordinary catch-up only ever adds; this one takes away, and what it takes away is a change this
    device already saw as committed.

    SO THE DEVICE SAYS SO, AND ONLY SAYS SO. `_warn_reached_by_revert` shows a warning after the
    adoption. Not a confirmation: the demotion already happened, a holder of this wallet's K_auth
    issued it behind a hold-to-confirm screen, and the WM accepted it. This device is catching up
    to what the wallet already is, and refusing would not undo anything -- it would only leave the
    device unable to sync. A prompt answerable one way is an obstacle, not consent.

    DELIBERATELY NOT DONE: re-queuing the discarded changes. A rollback is a deliberate act, and
    republishing what it discarded is this device overruling another's decision -- with two
    devices it does not even terminate, since A reverts, B republishes and A reverts again.

    A COUNT IS THE WHOLE ANSWER, decided rather than settled for. Naming the discarded entries
    would need the counter the restored root originally belonged to, which is not on
    `WardChainLink` and could only be put there inside `auth_commit`'s preimage -- anything
    outside the MAC is forgeable. What a user acts on is that the wallet went backwards and by how
    many steps; the entries themselves are what the next read shows against the restored tree.
    """
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")
    here_counter, here_root = store.counter, store.root()

    # The state the wallet held BEFORE this device's last write -- a1 alone. This is what the
    # demotion restores, and it sits below `here_counter`.
    restored = _subset(store, [k1])
    assert restored.root() != here_root

    # elsewhere: one ordinary write, then a demotion back past both of them
    mid = _subset(store, [])
    links = [
        _link(here_counter, here_root, here_counter + 1, mid.root()),
        _revert_link(
            here_counter + 1, mid.root(), here_counter + 2, restored.root()
        ),
    ]
    target = here_counter + 2

    wm = _wm_for(store)
    ack = ward.sync(session)
    root = restored.root()
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, target, root, links), _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target)
    ward.ingest_attestation(session, *_step_into(store, target, root, links), target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target)

    # ONE REQUEST: the host serves both predecessors in a single ack, since `_serves` walks the
    # chain it was given. Then the WARNING, then the ack.
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [
                m.WardChainRequest,
                m.ButtonRequest(name="ward_chain_revert"),
                m.WardVerifyChainAck,
            ]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        res = ward.verify_chain(session, _serves(links))

    # THE SCREEN IS THE POINT. Adoption already happened and cannot be refused -- declining would
    # not undo the demotion, only leave this device unable to sync -- so this is told, not asked.
    # What must not happen is silence: a change the user approved is gone.
    assert "discarded" in rec.text
    assert "1 change" in rec.text
    # ...and the same count goes back to the host, for a UI that wants to say it too
    assert res.reverts_crossed == 1

    # A HIGHER COUNTER CARRYING AN OLDER TREE. Both halves matter: the counter must advance or the
    # device would be going backwards, and the root must be the old one or nothing was restored.
    assert res.counter == target
    assert res.new_root == restored.root()
    assert res.new_root != here_root

    # the restored tree is what reads verify against now, and the entry that survived the
    # demotion still opens
    restored.counter = target
    _res, rec = _read(
        session, restored, lambda p: ward.get_entry(session, _APP, b"a", p)
    )
    assert "one" in rec.text


@pytest.mark.models("core")
def test_ward_verify_chain_brings_a_fresh_session_online(session: Session):
    """Adopting through the chain latches the session online, exactly as reconcile does.

    Both routes end in the same place -- a head bound to a WM attestation -- and this one is
    the STRICTER, since it also proves authorised descent from the head the device already
    held. It nevertheless used to leave the session OFFLINE: `reconcile` called `mark_online`
    and `verify_chain` did not. Every read then fell back to the offline store and every write
    refused, with nothing on screen to say why.

    IT HID BECAUSE THE LATCH IS PER SESSION WHILE THE ROOT IS IN FLASH. Any test that seeds an
    entry has already reconciled, so it is online long before the chain is exercised -- which is
    why `test_ward_catches_up_across_transitions_it_never_saw` reads successfully either way. A
    fresh session is what separates the two, and it is also the real case: multi-device catch-up
    arrives on a connection that has not reconciled, so the stronger route was precisely the one
    a device could not come online by.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"Petr_label")

    # A new session starts offline; the stored root survives -- see
    # `test_ward_root_survives_a_new_session`.
    fresh = session.test_ctx.get_session()

    # Confirm the head the device already holds, by the chain route rather than reconcile.
    # NO LINKS: the attested head IS the device's head, so there is nothing to fold. The empty
    # chain is the "what I hold is current" case, and the terminal counter and root checks still
    # have to agree -- so this exercises adoption without needing transitions to invent.
    wm = _wm_for(store)
    ack = ward.sync(fresh)
    root = store.root()
    wm.install_unauthenticated(
        ack.ward_id,
        store.counter,
        root,
        _T0 + store.counter,
        *_step_into(store, store.counter, root),
    )
    fc, fr, fhn, c, r, hn, _t, sig = wm.attest(ack.ward_id, ack.nonce)
    ward.ingest_attestation(fresh, fc, fr, c, r, sig, fhn, hn, _T0 + store.counter)

    res = ward.verify_chain(fresh, _serves([]))
    assert res.counter == store.counter
    assert res.new_root == store.root()

    # THE ASSERTION. A read only reaches the host once the session is online -- offline it is
    # served from the device's own store and never emits `WardEntryRequest` at all -- so
    # `_read`'s expected-response check is itself the test, and the value merely confirms the
    # answer came from the tree the chain adopted.
    _res, rec = _read(fresh, store, lambda p: ward.get_entry(fresh, _APP, b"addr1", p))
    assert "Petr_label" in rec.text


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

    wm = _wm_for(store)
    ack = ward.sync(session)
    target = base_counter + 2
    root = head.root()
    # THE ATTESTATION IS CONTIGUOUS, deliberately -- a WM only ever advances its head one counter
    # at a time, so it would never sign the jump itself, and an attestation that did is refused at
    # ingest rather than in the walk. Naming `target - 1` puts the gap where this test wants it:
    # in the LINK, so `verify_chain_step_back` is the thing that refuses it.
    sig = wm.sign(
        ack.ward_id, ack.nonce, target - 1, base_root, _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target
    )
    ward.ingest_attestation(
        session, target - 1, base_root, target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target
    )

    with pytest.raises(exceptions.TrezorFailure, match="exactly one"):
        ward.verify_chain(session, _serves(links))


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

    wm = _wm_for(store)
    ack = ward.sync(session)
    root = head.root()
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, target, root, links), _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target)
    ward.ingest_attestation(session, *_step_into(store, target, root, links), target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target)

    with pytest.raises(
        exceptions.TrezorFailure, match="does not descend from this device's head"
    ):
        ward.verify_chain(session, _serves(links))


@pytest.mark.models("core")
def test_ward_refuses_an_unauthorised_link(session: Session):
    """Without K_auth a link cannot be minted, so the host cannot invent a step."""
    store = WardTrie()
    k1 = _seed(session, store, b"a", b"one")
    base_counter, base_root = store.counter, store.root()
    head = _subset(store, [k1])
    target = base_counter + 1

    forged = [(base_counter, base_root, target, head.root(), bytes(32))]

    wm = _wm_for(store)
    ack = ward.sync(session)
    root = head.root()
    # A SYNTHETIC STEP OUT OF THE DEVICE'S HEAD, so its nonces are the pair such a step would
    # have: it CONSUMES the one the device latched -- otherwise the continuity rule refuses it a
    # gate before the MAC, and this test would stop exercising `verify_chain_step_back` -- and
    # mints a new one, since every real step rotates.
    consumed = wm.head_nonce(ack.ward_id)
    minted = bytes([0x8B]) * 32
    sig = wm.sign(
        ack.ward_id, ack.nonce, *_step_into(store, target, root, forged), consumed, target, root, minted, _T0 + target
    )
    ward.ingest_attestation(
        session, *_step_into(store, target, root, forged), target, root, sig, consumed, minted, _T0 + target
    )

    # The attestation names the step this forged link claims, so the walk gets as far as the MAC
    # -- which is the check under test. Naming anything else would refuse it a gate earlier, on
    # the predecessor, and this test would stop exercising `verify_chain_step_back`.
    with pytest.raises(exceptions.TrezorFailure, match="not authorised"):
        ward.verify_chain(session, _serves(forged))


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

    wm = _wm_for(store)
    ack = ward.sync(session)
    root = attested.root()  # attests a different root than the walk will reach
    sig = wm.sign(ack.ward_id, ack.nonce, *_step_into(store, target, root, links), _nonces(wm, ack.ward_id)[0], target, root, wm.head_nonce(ack.ward_id), _T0 + target)
    ward.ingest_attestation(session, *_step_into(store, target, root, links), target, root, sig, _nonces(wm, ack.ward_id)[0], wm.head_nonce(ack.ward_id), _T0 + target)

    # SERVED UNCONDITIONALLY, not through `_serves`. The anchor is the ATTESTED root now, so an
    # HONEST host would filter this link out -- it ends somewhere the device never asked about --
    # and the walk would die on "the host cannot continue the chain" without the firmware's
    # end-of-link check ever running. A MISBEHAVING host is exactly what that check exists for,
    # so the source here answers every request with the same wrong link.
    with pytest.raises(exceptions.TrezorFailure, match="does not end at the running root"):
        ward.verify_chain(session, lambda _tc, _tr, _limit: links)


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


def _rollback(
    session: Session,
    wm: MockWM,
    store: WardTrie,
    recovered_root,
    wm_counter: "int | None" = None,
    wm_root=None,
):
    """Walk the demotion confirmation and return (ack, recorder).

    `wm_counter`/`wm_root` stage a REGRESSED WM -- its register restored from a backup, which
    `install_unauthenticated` models exactly: a WM told a head by a party holding no signature.
    Omit them for the ordinary case, where the WM is at this device's head and the demotion is
    what used to be called a rollback. The handler cannot tell the two apart, which is the point
    of having one.
    """
    if wm_counter is None:
        wm_counter, wm_root = store.counter, store.root()
    else:
        wm.install_unauthenticated(
            _WARD_ID,
            wm_counter,
            wm_root,
            _T0 + wm_counter,
            *_step_into(store, wm_counter, wm_root),
        )

    ack_sync = ward.sync(session)
    fc, fr, fhn, tc, tr, hn, ts, sig = wm.attest(ack_sync.ward_id, ack_sync.nonce)

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            [m.ButtonRequest(name="ward_rollback"), m.WardRollbackAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        ack = ward.rollback(
            session,
            fc,
            fr,
            tc,
            tr,
            sig,
            fhn,
            hn,
            recovered_root=recovered_root,
            timestamp=ts,
        )
    return ack, rec


def _publish_demotion(wm: MockWM, store: WardTrie, ack, from_counter: int, from_root) -> tuple:
    """Put the minted demotion into the WM, as a host does, and record it in the log.

    THE WM VERIFIES IT like any other advance: compare-and-swap on the head it holds, and
    `wm_sig` under the REVERT tag. A demotion the WM refuses simply does not happen.
    """
    wm.advance(
        _WARD_ID,
        from_counter,
        from_root,
        ack.counter,
        ack.new_root,
        ack.wm_sig,
        _T0 + ack.counter,
    )
    link = (from_counter, from_root, ack.counter, ack.new_root, ack.auth_commit)
    store.links.append(link)
    store.wm_sigs[ack.counter] = ack.wm_sig
    store.counter = ack.counter
    return link


def _adopt_demotion(session: Session, wm: MockWM, store: WardTrie, ack, link):
    """Publish, attest and adopt -- the round trip a host runs after a demotion is minted."""
    fc, fr, fhn, tc, tr, hn, ts, sig = wm.attest(_WARD_ID, ward.sync(session).nonce)
    ward.ingest_attestation(session, fc, fr, tc, tr, sig, fhn, hn, ts)
    ward.reconcile(session, link)


@pytest.mark.models("core")
def test_ward_rollback_undoes_the_last_write(session: Session):
    """The wallet returns to the state before its most recent change.

    THE COUNTER STILL GOES FORWARD. Reusing it would let the undone write replay, since its own
    authorisation names that counter -- and it is also what lets the WM accept the demotion as an
    ordinary advance, needing no special handling.
    """
    store = WardTrie()
    key_a = _seed(session, store, b"a", b"one")
    before_root = store.root()
    _seed(session, store, b"b", b"two")

    wm = _wm_for(store)
    _attest(session, wm, store)
    ack, rec = _rollback(session, wm, store, before_root)

    assert ack.counter == store.counter + 1  # forward, though the head moves back
    assert ack.new_root == before_root
    assert "revert" in rec.title.lower()
    assert "cannot be recovered" in rec.text.lower()

    from_counter, from_root = store.counter, store.root()
    link = _publish_demotion(wm, store, ack, from_counter, from_root)
    _adopt_demotion(session, wm, store, ack, link)

    rewound = _subset(store, [key_a])
    rewound.counter = ack.counter
    assert rewound.root() == before_root
    _res, rec = _read(
        session, rewound, lambda p: ward.get_entry(session, _APP, b"b", p)
    )
    assert "entry not found" in rec.title


@pytest.mark.models("core")
def test_ward_rollback_needs_no_proof_that_the_target_was_ever_the_head(session: Session):
    """A demotion asks for the WM's head and the user, and nothing else.

    It briefly asked for the archived attestation of its TARGET, so that a link from an abandoned
    branch could not be restored -- and before that, for a link at all. Both are withdrawn,
    because they ask for something this situation cannot supply: a rollback runs when the host
    cannot reconstruct the current tree, so the state it CAN rebuild is whatever its own rows
    hash to, and a host missing rows is exactly one whose reconstructible root the WM may never
    have attested, and which no link ever ended at.

    So the target here is a tree that NEVER EXISTED in this wallet's history -- assembled from
    leaves it holds, in a shape it never had -- and it is accepted, on the user's approval alone.
    """
    store = WardTrie()
    key_a = _seed(session, store, b"a", b"one")
    key_b = _seed(session, store, b"b", b"two")
    _seed(session, store, b"c", b"three")

    # a and c but not b: a shape no counter of this wallet ever held
    invented = _subset(store, [key_a, _seed(session, store, b"d", b"four")])
    assert invented.root() != store.root()
    del key_b

    wm = _wm_for(store)
    _attest(session, wm, store)
    ack, rec = _rollback(session, wm, store, invented.root())

    assert ack.new_root == invented.root()
    # AND THE SCREEN SAYS WHAT IS NOT PROVEN. With no headship proof asked for, a user reading
    # "confirmed by the WARD Manager" would be reading a guarantee nobody made.
    assert "not confirmed" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_rollback_count_comes_from_the_attested_counter(session: Session):
    """The number on the screen is authenticated, which is what makes it worth showing.

    A host that wants a deep demotion approved would like the screen to read "1 change" rather
    than "3 changes", since the count is the only thing separating an honest recovery from a
    rewind. It cannot choose it: the distance is `stored_counter - (attested_counter + 1)`, and
    both numbers come from verified material -- the device's own head, and a counter inside the
    WM's signed attestation.
    """
    store = WardTrie()
    key_a = _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")
    _seed(session, store, b"c", b"three")
    _seed(session, store, b"d", b"four")
    assert store.counter == 4

    wm = _wm_for(store)
    _attest(session, wm, store)

    # The WM's register regressed to counter 1, so the demotion lands at 2 and discards two.
    at_one = _link_into(store, 1)
    _ack, rec = _rollback(
        session, wm, store, _subset(store, [key_a]).root(), at_one[2], at_one[3]
    )

    assert "#4" in rec.squashed  # where it is
    assert "#2" in rec.squashed  # where it is going
    assert "2changes" in rec.squashed  # and the distance, from authenticated numbers


@pytest.mark.models("core")
def test_ward_rollback_from_a_regressed_wm_is_the_same_operation(session: Session):
    """The WM's register is lost; the demotion extends the WM's head, not this device's.

    THAT IS THE WHOLE DIFFERENCE between what used to be two messages. A device only ever adopts
    what the WM attested, so normally the two heads are the same and this is an ordinary
    rollback. When they differ, building from the WM's is the only thing it will
    compare-and-swap against -- and the handler does not have to know which case it is in.

    The counter it lands on is BELOW this device's floor, so the adoption needs the consent
    recorded at the hold; one hold buys one descent.
    """
    store = WardTrie()
    key_a = _seed(session, store, b"a", b"one")
    wm = _wm_for(store)
    _attest(session, wm, store)
    wm_counter, wm_root = store.counter, store.root()

    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"b", b"two", p),
        "ward_set_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)
    _attest(session, wm, store)
    assert store.counter > wm_counter

    serviceable = _subset(store, [key_a])
    ack, _rec = _rollback(
        session, wm, store, serviceable.root(), wm_counter, wm_root
    )

    assert ack.counter == wm_counter + 1
    assert ack.new_root == serviceable.root()

    # NOTHING ADOPTED YET: the head moves when the WM confirms, like every other write.
    assert ward.sync(session).counter > wm_counter

    link = _publish_demotion(wm, store, ack, wm_counter, wm_root)
    _adopt_demotion(session, wm, store, ack, link)

    serviceable.counter = ack.counter
    _res, rec = _read(
        session, serviceable, lambda p: ward.get_entry(session, _APP, b"a", p)
    )
    assert "one" in rec.text
    assert ward.sync(session).counter == ack.counter

    # AND THE CONSENT IS SPENT. A second attestation below the floor, however genuine, has no
    # approval left to ride on.
    behind = ack.counter - 1
    ack_sync = ward.sync(session)
    sig2 = wm.sign(
        ack_sync.ward_id, ack_sync.nonce, behind - 1, wm_root, _nonces(wm, ack_sync.ward_id)[0], behind, wm_root, wm.head_nonce(ack_sync.ward_id), _T0
    )
    with pytest.raises(exceptions.TrezorFailure, match="older than the stored counter"):
        ward.ingest_attestation(
            session, behind - 1, wm_root, behind, wm_root, sig2, _nonces(wm, ack_sync.ward_id)[0], wm.head_nonce(ack_sync.ward_id), _T0
        )


@pytest.mark.models("core")
def test_ward_rollback_still_requires_a_genuine_attestation(session: Session):
    """Consent does not replace verification.

    The user's approval covers "go back to this state", not "trust whoever said so": the WM's
    signature over its own head is checked against this round's nonce exactly as on the ordinary
    path, and it fails before any screen -- so no input flow here.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    wm = _wm_for(store)
    _attest(session, wm, store)
    root = store.root()

    impostor = MockWM(seed=b"NOT THE WARD MANAGER DEBUG KEY!!")
    ack = ward.sync(session)
    step = _step_into(store, store.counter, root)
    from_head_nonce, head_nonce = _nonces(wm, ack.ward_id)
    sig = impostor.sign(
        ack.ward_id,
        ack.nonce,
        *step,
        from_head_nonce,
        store.counter,
        root,
        head_nonce,
        store.timestamp,
    )
    with pytest.raises(
        exceptions.TrezorFailure, match="attestation verification failed"
    ):
        ward.rollback(
            session,
            *step,
            store.counter,
            root,
            sig,
            from_head_nonce,
            head_nonce,
            recovered_root=root,
            timestamp=store.timestamp,
        )


def _branch_sibling_case(session: Session):
    """A store where deleting one entry collapses a branch whose sibling is a BRANCH.

    That was the hard case: a branch sibling's hash used to go stale the instant it moved
    up a level. It promotes unchanged now, so this is only interesting as a regression
    shape -- but it is the shape two implementations got wrong, so it stays covered.

    Found by writing real entries until one appears, so the keys are whatever the device's
    HMAC produces. Skips rather than passing vacuously if this seed yields none.
    """
    store = WardTrie()
    for i in range(6):
        _seed(session, store, b"addr%d" % i, b"v%d" % i)
        for key in list(store.blobs):
            proof = store.membership_proof(key)
            if not proof:
                continue
            # the collapsing sibling is a branch exactly when removing this leaf leaves
            # more than one key on the other side of the deepest branch
            split0 = int.from_bytes(proof[0][0:2], "big")
            others = [
                k
                for k in store.blobs
                if k != key and addr_bit(k, split0) != addr_bit(key, split0)
            ]
            if len(others) > 1:
                return store, key
    pytest.skip("no branch-sibling delete arises for this seed")


# REMOVED: test_ward_delete_refuses_a_sibling_it_cannot_classify. It asserted that a delete
# withholding the sibling's KIND was refused, which was necessary while a node's hash
# committed to its depth: a branch sibling had to arrive decomposed so the device could
# re-derive it, a leaf did not, and the proof could not say which it was. With depth out of
# the preimage both promote unchanged, so there is nothing to withhold and nothing to refuse.
# The canonical outcome is still asserted by the test below and by the differential harness.


@pytest.mark.models("core")
def test_ward_delete_keeps_the_root_canonical_when_a_branch_is_promoted(
    session: Session,
):
    """A branch sibling promotes unchanged, and the device stays on the CANONICAL root.

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
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, identifier, p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)
    assert key not in store.blobs
    assert len(store) > 1  # a branch sibling survived, which is the case under test

    remaining = next(
        i for i in names if expected_entry_key(_K_PATH, _APP, i) in store.blobs
    )
    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, remaining, p)
    )
    assert "entry not found" not in rec.title

    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, remaining, b"still_writable", p),
        "ward_set_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)


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
    assert (
        stale.root() is not None
    )  # the replay it will attempt is a real, provable tree

    res, _rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)
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
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)
    assert len(store) == 0

    _seed(session, store, b"addr2", b"after_the_purge")
    assert len(store) == 1
    _res, rec = _read(
        session, store, lambda p: ward.get_entry(session, _APP, b"addr2", p)
    )
    assert "after_the_purge" in rec.squashed


# --- asking the device where its head is --------------------------------------------


@pytest.mark.models("core")
def test_ward_sync_reports_the_device_counter(session: Session):
    """The round opener also answers "where are you".

    Weak on its own -- it would pass on a field nothing consumes -- which is why the test
    below is the one that matters. This one pins the value.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    _seed(session, store, b"addr2", b"w")

    ack = ward.sync(session)
    assert ack.counter == store.counter
    assert ack.counter > 0  # two writes happened; a zero here would pass vacuously


@pytest.mark.models("core")
def test_ward_sync_counter_reports_the_confirmed_head(session: Session):
    """WardSyncAck.counter reports the confirmed head, which is now the only head there is.

    The field was added so a host could discover that a write it never saw acknowledged had
    nonetheless landed. Commit-on-confirmation removes that possibility outright: an
    unacknowledged write cannot have landed, because landing IS the round the host drives. So
    the field keeps a smaller job -- telling a host where the device is, after a restart or
    before it starts publishing -- and this test pins that, including that an unconfirmed
    write does not move it.
    """
    store = WardTrie()
    _seed(session, store, b"a", b"one")
    _seed(session, store, b"b", b"two")
    assert ward.sync(session).counter == store.counter

    _res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"c", b"three", p),
        "ward_set_entry",
    )
    assert ward.sync(session).counter == store.counter


@pytest.mark.models("core")
def test_ward_write_authorises_its_transition_over_mac_heads(session: Session):
    """Every write carries an authorisation over the transition it made.

    WHAT THIS USED TO ASSERT. The ack also carried `auth_sig` -- Ed25519 under K_sig over the
    ROOT transition, nominally for the WM. It was removed: nothing verified it, in firmware or
    in the mock WM, and nothing safely could. The WM compare-and-swaps on `(counter, mac)`,
    which a root-naming signature did not bind. The WM-facing authorisation is `wm_sig`, which
    the connect path does not carry yet.

    WHAT REMAINS, AND WHY IT IS NOW THE WHOLE STORY. `auth_commit` under K_auth is what another
    device of this wallet folds when it walks the history, and it covers the ROOT transition
    directly -- K_mac and the mac-head layer are gone. It is also the only thing that can refuse
    a WM naming a state this wallet never reached, since minting one needs the seed.
    """
    store = WardTrie()
    _go_online(session, store)
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"v", p),
        "ward_set_entry",
    )

    assert res.auth_commit is not None
    assert len(res.auth_commit) == 32

    from_root = None  # the first write starts from an empty tree
    ward.apply(store, res)  # so the store can tell us the root the transition landed on

    assert res.auth_commit == auth_commit(
        _K_AUTH, _WARD_ID, res.counter - 1, from_root, res.counter, store.root()
    )

    # ...and it is bound to those endpoints: a different destination does not reproduce it
    assert res.auth_commit != auth_commit(
        _K_AUTH,
        _WARD_ID,
        res.counter - 1,
        from_root,
        res.counter + 1,
        store.root(),
    )

    # the preimage really does name ROOTS, and the empty tree as EMPTY_ROOT
    pre = transition_preimage(
        TAG_COMMIT, _WARD_ID, res.counter - 1, from_root, res.counter, store.root()
    )
    assert pre[1 + len(TAG_COMMIT) :].startswith(_WARD_ID)
    assert pre.endswith(store.root())


# --- the offline store ------------------------------------------------------------
#
# Two hosts drive this. A host that does not speak WARD never sends WardSync, cannot answer
# WardEntryRequest, and must be served from what the device already holds. And Suite, before
# the trie lands, can push entries while the counter is still zero -- so the store has to work
# in exactly the state where the device holds no trusted root.
#
# The rule everything below is really testing: a record may go stale, be superseded, or become
# unreadable, and NONE of that lets the device delete it. Only a user-confirmed erase does.


def _pin(session: Session, store: WardTrie, identifier: bytes, br_name: str) -> tuple:
    """Pin an entry, walking its screen. Returns (result, recorder)."""
    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected(br_name, reveals=m.WardPinCachedEntry))
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        res = ward.pin_cached_entry(
            session, _APP, identifier, ward.store_provider(store)
        )
    return res, rec


def _offline_read(session: Session, identifier: bytes) -> "_Recorded":
    """EXPORT from the DEVICE'S store, and assert it asks the host NOTHING.

    `WardQueueGetEntry` is a different request from `WardGetEntry` rather than a mode of it, so
    there is no provider to pass and no pull to answer. The absent WardEntryRequest in the
    expected sequence is still the assertion: a local read that pulled would mean this path can
    be reached from a FAILED pull, and a hostile host could then force an old value onto the
    screen by answering badly on purpose.
    """
    rec = _Recorded()

    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueGetEntry)
            + [m.ButtonRequest(name="ward_queue_get_entry"), m.WardQueueGetAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        rec.ack = ward.queue_get_entry(session, _APP, identifier)
    return rec


@pytest.mark.models("core")
def test_ward_offline_read_serves_the_pinned_value(session: Session):
    """The motivating case: a host that never syncs is still served.

    A new session starts offline, so the read below happens in exactly the state a
    WARD-unaware host leaves the device in -- and it is answered from flash, with wording
    that says so rather than borrowing the verified read's.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"bc1qkeptoffline")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    fresh = session.test_ctx.get_session()
    rec = _offline_read(fresh, b"addr1")

    assert "offline copy" in rec.title
    assert "bc1qkeptoffline" in rec.squashed


@pytest.mark.models("core")
def test_ward_pinned_entry_survives_a_power_cycle(session: Session):
    """Flash, not the session cache. A store that forgot here would serve only the session
    that wrote it, which is the state this feature exists to leave."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"persist_me")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    fresh = session.test_ctx.get_session()

    rec = _offline_read(fresh, b"addr1")
    assert "persist_me" in rec.squashed


@pytest.mark.models("core")
def test_ward_offline_read_of_an_unpinned_entry_says_so(session: Session):
    """A miss is reported as a miss -- never as an empty value, and never by pulling."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")

    fresh = session.test_ctx.get_session()
    rec = _offline_read(fresh, b"addr1")

    assert "not kept offline" in rec.title


@pytest.mark.models("core")
def test_ward_pin_at_counter_zero_is_allowed(session: Session):
    """Bootstrap: with no trie on the host there is no proof and no root, so the AEAD is the
    whole of the evidence -- and pinning adds no new trust assumption, because a READ in this
    state already displays exactly these bytes on exactly this evidence.

    What it cannot show is freshness, and nothing pretends otherwise: the record stores no counter,
    so a local read says only that this copy has not been checked against a host.
    """
    key = expected_entry_key(_K_PATH, _APP, b"addr1")

    # A leaf sealed by ANOTHER device of this wallet, served to one that has never synced.
    # It has to come from the oracle: the moment this device syncs it learns the tree is
    # EMPTY, and from then on it rightly refuses any leaf claiming to be in it -- so the
    # state under test cannot be reached through a local write. See tests/ward_keys.py.
    leaf = ward.Leaf(
        seal_identity(_K_IDENT, key, "address", b"addr1", _APP),
        seal_content(_K_DATA, key, "address", b"bootstrap_value"),
    )

    def provider(_entry_key: bytes) -> ward.Answer:
        # No proof, and none is asked for: the device holds no root to check one against.
        return ward.Answer(leaf=leaf)

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(_expected("ward_pin_cached_entry", reveals=m.WardPinCachedEntry))
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        ward.pin_cached_entry(session, _APP, b"addr1", provider)

    assert "keep for offline use" in rec.title
    assert "bootstrap_value" in rec.squashed

    read = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "bootstrap_value" in read.squashed
    # Authentic, with nothing claiming it is current.
    assert "not checked against the host" in read.text.lower()


@pytest.mark.models("core")
def test_ward_pin_rejects_a_forged_leaf(session: Session):
    """A leaf the wallet never sealed fails its tag, and NOTHING is stored.

    The negative half of the bootstrap argument: "the AEAD is the only check" is only
    acceptable while the AEAD actually refuses everything a host can make up.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"genuine")

    key = expected_entry_key(_K_PATH, _APP, b"addr1")
    good = store.blobs[key]
    forged = m.WardLeafContent(
        encoding=0,
        encrypted=m.WardEncryptedLeaf(
            nonce=good.content.encrypted.nonce,
            tag=good.content.encrypted.tag,
            ct=bytes(len(good.content.encrypted.ct)),  # replaced ciphertext
        ),
    )

    def provider(entry_key: bytes) -> ward.Answer:
        answer = ward.store_provider(store)(entry_key)
        return ward.Answer(
            leaf=ward.Leaf(answer.leaf.identity, forged),
            proof=answer.proof,
            witness_entry_key=answer.witness_entry_key,
            witness_commit=answer.witness_commit,
        )

    with pytest.raises(exceptions.TrezorFailure):
        ward.pin_cached_entry(session, _APP, b"addr1", provider)

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "not kept offline" in rec.title


@pytest.mark.models("core")
def test_ward_pin_rejects_a_leaf_that_is_not_in_the_trusted_root(session: Session):
    """Once the device holds a root, membership is required -- authenticity is not enough.

    The leaf here is genuine: the device sealed it, and its tag verifies. It simply is not in
    the tree the device trusts, which is exactly the shape of a host replaying an old value.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"first")
    stale = {k: v for k, v in store.blobs.items()}
    _seed(session, store, b"addr1", b"second")

    def provider(entry_key: bytes) -> ward.Answer:
        # a real leaf, proved against the tree it belonged to a counter ago
        old = WardTrie()
        for k, v in stale.items():
            old.set(k, v)
        return ward.store_provider(old)(entry_key)

    with pytest.raises(exceptions.TrezorFailure):
        ward.pin_cached_entry(session, _APP, b"addr1", provider)


@pytest.mark.models("core")
def test_ward_a_pinned_entry_survives_the_head_moving(session: Session):
    """Advancing the head leaves a record alone -- it is not rewritten and not removed.

    It used to also change what the record READ as: a stored counter was compared against the
    trusted one and the screen said "may be out of date". No counter is stored now, so a local copy
    always reads as unchecked rather than sometimes as stale. Weaker wording, same record: moving the
    head still never writes to the store, which is what keeps it from acquiring a reason to delete.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"pinned_value")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    _seed(session, store, b"other", b"moves_the_head")

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "pinned_value" in rec.squashed
    assert "not checked against the host" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_repinning_an_identical_value_neither_asks_nor_writes(session: Session):
    """Nothing was replaced, so there is nothing to authorise.

    A confirmation on a no-op is worse than no confirmation: it is a hold that always means
    "nothing happened", which is the kind of screen that gets approved without being read.

    THE REVEAL SCREEN IS NOT AN EXCEPTION TO THAT and is asked anyway on a device with no app role,
    because it is answered before the device has looked and therefore before it can know this is a
    no-op. It says something different in any case -- it is about being shown a stored value, not
    about a change -- and the assertion that matters here survives either way: no
    `ward_pin_cached_entry`, and no write.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"same_value")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    with session.test_ctx as ctx:
        # No ButtonRequest of the operation's own -- the device pulls, sees identical bytes, and
        # stops. Only the reveal screen precedes it, and only where there is no app role.
        ctx.set_expected_responses(
            reveal_prefix(m.WardPinCachedEntry) + [m.WardEntryRequest, m.Success]
        )
        ward.pin_cached_entry(session, _APP, b"addr1", ward.store_provider(store))


@pytest.mark.models("core")
def test_ward_replacing_a_pinned_value_needs_its_own_confirmation(session: Session):
    """Replacement destroys the previous copy, so it is confirmed like a deletion.

    The screen must show BOTH values: confirming a replacement without naming what is being
    lost tells the user nothing they could act on.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"value_one")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    _seed(session, store, b"addr1", b"value_two")
    _res, rec = _pin(session, store, b"addr1", "ward_replace_cached_entry")

    assert "replace offline copy" in rec.title
    assert "value_one" in rec.squashed
    assert "value_two" in rec.squashed

    read = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "value_two" in read.squashed


@pytest.mark.models("core")
def test_ward_cancelling_a_replacement_leaves_the_old_copy(session: Session):
    store = WardTrie()
    _seed(session, store, b"addr1", b"keep_this")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")
    _seed(session, store, b"addr1", b"reject_this")

    with session.test_ctx as ctx:
        ctx.set_input_flow(reject_flow(session))
        with pytest.raises(exceptions.Cancelled):
            ward.pin_cached_entry(session, _APP, b"addr1", ward.store_provider(store))

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "keep_this" in rec.squashed
    assert "reject_this" not in rec.squashed


@pytest.mark.models("core")
def test_ward_erase_removes_the_copy_only_after_confirmation(session: Session):
    store = WardTrie()
    _seed(session, store, b"addr1", b"erase_me")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    # cancelled: flash untouched
    with session.test_ctx as ctx:
        ctx.set_input_flow(reject_flow(session))
        with pytest.raises(exceptions.Cancelled):
            ward.erase_cached_entry(session, _APP, b"addr1")

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "erase_me" in rec.squashed

    # confirmed: gone
    erased = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            # The offline read above ran on a session of its own, so on v1 this pays to come back.
            session_switch_prefix()
            + reveal_prefix(m.WardEraseCachedEntry)
            + [m.ButtonRequest(name="ward_erase_cached_entry"), m.Success]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=erased.on_page).get()
        )
        ward.erase_cached_entry(session, _APP, b"addr1")

    assert "remove offline copy" in erased.title
    assert "erase_me" in erased.squashed  # named what was being lost

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "not kept offline" in rec.title


@pytest.mark.models("core")
def test_ward_erasing_something_not_kept_is_a_silent_no_op(session: Session):
    """No screen, because a hold that always means "nothing happened" trains the user to
    approve without reading -- the same reasoning as the idempotent delete."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")

    with session.test_ctx as ctx:
        ctx.set_expected_responses(reveal_prefix(m.WardEraseCachedEntry) + [m.Success])
        ward.erase_cached_entry(session, _APP, b"addr1")


@pytest.mark.models("core")
def test_ward_deleting_an_entry_leaves_the_offline_copy(session: Session):
    """Two different questions, and one confirmation cannot stand for both.

    The user held to remove the ENTRY. They were never asked about the copy they deliberately
    chose to keep on this device, so it stays until they say otherwise.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"still_local")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    res, _rec = _write(
        session,
        store,
        lambda p: ward.delete_entry(session, _APP, b"addr1", p),
        "ward_delete_entry",
    )
    ward.apply(store, res)
    _confirm(session, store)

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "still_local" in rec.squashed


# --- the queue --------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_offline_write_is_queued_not_applied(session: Session):
    """With no host to pull from there is no current state, so no root and no counter can be
    derived. The device holds the intent and SAYS SO -- an ack that looked like a write would
    make the user's confirmation retroactively untrue.

    It says so by the MESSAGE TYPE: `WardQueueSetAck` carries a path and nothing else, so there
    is no leaf-shaped answer for a host to store and no flag it can fail to read."""
    rec = _Recorded()

    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueSetEntry)
            + [m.ButtonRequest(name="ward_queue_entry"), m.WardQueueSetAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        ack = ward.queue_set_entry(session, _APP, b"addr1", b"queued_value")

    # An EMPTY ack: the TYPE is what says the change was only held, so there is no field on it to
    # misread -- not a leaf, not a counter, and not even the path, which nothing needs until the
    # change reaches the tree.
    assert not ack.FIELDS
    assert isinstance(ack, m.WardQueueSetAck)
    assert "queue" in rec.title
    assert "not applied yet" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_a_queued_write_outlives_the_session_that_made_it(session: Session):
    """Flash, not the session cache -- and the session is the thing that would lose it.

    A queue held in RAM would make the confirmation a lie: the user holds, the session drops,
    the change is gone and nothing said so. A new session is the sharpest available test of
    that, since it is exactly what clears everything except flash.
    """

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"survives")

    fresh = session.test_ctx.get_session()

    rec = _offline_read(fresh, b"addr1")
    assert "queued change" in rec.title  # the export screen; still the pending record
    assert rec.ack.pending is True
    assert "survives" in rec.squashed


@pytest.mark.models("core")
def test_ward_flush_publishes_the_queued_change_sealed(session: Session):
    """Sealing happens on the way OUT, which is the whole reason records sit in flash in the
    clear: `storage.c` covers them until they leave the device, and not after.

    The change is also RE-DERIVED here. It was formed with no root to derive against, so the
    flush pulls the path's present leaf, proves it, and only then computes a new root.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"published_value")

    _go_online(session, store)

    res = ward.flush_queue(session, ward.store_provider(store))
    # A published queued change is an ordinary leaf, reported by the one ack type that also
    # carries `remaining` -- which a direct write has nothing to count and therefore never has.
    assert isinstance(res.response, m.WardFlushQueueAck)
    assert res.counter is not None
    assert res.auth_commit is not None
    assert res.remaining == 0

    # the content really is sealed, and opens to what was queued
    value = unpack_content(
        open_content(_K_DATA, res.entry_key, "address", res.leaf.content.encrypted)
    )[1]
    assert value == b"published_value"


@pytest.mark.models("core")
def test_ward_flush_needs_a_synced_session(session: Session):
    """With no trusted root there is nothing to derive against and nothing to prove the
    pulled leaf with. Refusing is the honest answer."""
    with pytest.raises(exceptions.TrezorFailure, match="sync"):
        ward.flush_queue(session, lambda _k: ward.Answer())


@pytest.mark.models("core")
def test_ward_a_change_stays_queued_until_the_wm_confirms_it(session: Session):
    """Handing the leaf to the host is not the change taking effect.

    A host that never publishes leaves the change queued and re-sendable -- fail-closed and
    recoverable, rather than a silent loss. This is the same boundary an online write commits
    at, and the reason `reconcile` is where the flag comes off.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"unconfirmed")

    _go_online(session, store)
    ward.flush_queue(session, ward.store_provider(store))
    # The host neither stores the leaf nor publishes the counter -- the response was lost, as
    # far as it is concerned. The next round therefore attests the OLD head, and the device
    # must conclude its change did not land rather than that it did.
    _confirm(session, store)

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "queued change" in rec.title
    assert rec.ack.pending is True
    assert "unconfirmed" in rec.squashed


@pytest.mark.models("core")
def test_ward_an_offered_change_settles_in_a_later_session(session: Session):
    """The claim that settles a flush outlives the session that filed it.

    A flush marks the record OFFERED and files a claim saying which change was handed over and
    at which counter; the adoption that follows settles the two against each other. That claim
    used to live in the SESSION CACHE, so it was lost on exactly the events recovery depends
    on -- the channel closing, the cache being evicted, the device losing power. A record left
    PENDING|OFFERED with no claim is then stranded: both `next_unsent` and `count_unsent` skip
    an offered record, so `remaining` reports zero, the host's flush loop exits, and nothing
    ever offers it again. Stored, never sent, and invisible as a problem.

    So the flush and the adoption are deliberately put in DIFFERENT sessions here. Every other
    flush test reconciles in the same one, which is why none of them noticed.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"landed_later")

    _go_online(session, store)
    res = ward.flush_queue(session, ward.store_provider(store))
    ward.apply(store, res)
    _publish(_wm_for(store), res, store)

    # A NEW SESSION adopts the head the change is in. It shares the device's flash and nothing
    # of the session that offered the change.
    later = session.test_ctx.get_session()
    _confirm(later, store)

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "offline copy" in rec.title
    assert rec.ack.pending is None or rec.ack.pending is False
    assert "landed_later" in rec.squashed


@pytest.mark.models("core")
@pytest.mark.setup_client(passphrase=True)
def test_ward_one_wallet_does_not_settle_anothers_queued_change(
    test_ctx: TrezorTestContext,
):
    """Reconciling one hidden wallet must not touch another wallet's queued records.

    THIS GUARDS AN INVARIANT THE CLAIM JOURNAL PUTS AT RISK RATHER THAN A BUG IT FIXED. While
    claims lived in the session cache, isolation came for free: each passphrase opens its own
    session, so one wallet's reconcile simply could not see another's claims. The journal is
    flash and therefore GLOBAL, so the same isolation now has to be stated -- every claim
    carries the full 16-byte wallet_id and `reconcile_pending` filters on it.

    Two wallets share one record pool and one counter space, so without that filter a wallet
    that had advanced further would settle the other's offered change: PENDING cleared on a
    record whose change that wallet never published, whose value then survives as a supposed
    "offline copy" of something never written. Beta's counter is pushed past alpha's precisely
    so a counter comparison alone would say "landed".
    """
    alpha = test_ctx.get_session(passphrase="alpha")
    beta = test_ctx.get_session(passphrase="beta")

    store_a, store_b = WardTrie(), WardTrie()

    # Alpha offers a change and never learns whether it landed.
    with test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(alpha).get())
        ward.queue_set_entry(alpha, _APP, b"addr1", b"alphas_change")
    _go_online(alpha, store_a)
    ward.flush_queue(alpha, ward.store_provider(store_a))

    # Beta then advances its OWN head well past alpha's counter.
    for i in range(3):
        _seed(beta, store_b, b"b%d" % i, b"beta_value")
    assert store_b.counter > store_a.counter

    # Beta's adoption must leave alpha's record exactly as it was.
    _confirm(beta, store_b)

    rec = _offline_read(test_ctx.get_session(passphrase="alpha"), b"addr1")
    assert "queued change" in rec.title
    assert rec.ack.pending is True
    assert "alphas_change" in rec.squashed


@pytest.mark.models("core")
def test_ward_a_confirmed_change_becomes_an_offline_copy(session: Session):
    """Clearing the pending flag is a REWRITE, never a delete: the record stays on as the
    cached copy of the value that was just published."""
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"landed")

    _go_online(session, store)
    res = ward.flush_queue(session, ward.store_provider(store))
    ward.apply(store, res)
    _publish(_wm_for(store), res, store)
    _confirm(session, store)

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "offline copy" in rec.title
    assert "landed" in rec.squashed


@pytest.mark.models("core")
def test_ward_discarding_a_queued_change_is_confirmed_and_says_what_it_is(
    session: Session,
):
    """Erasing a pending record DISCARDS a change that was never published -- calling that a
    deletion would suggest WARD ever had it."""

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"discard_me")

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardEraseCachedEntry)
            + [m.ButtonRequest(name="ward_erase_cached_entry"), m.Success]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        ward.erase_cached_entry(session, _APP, b"addr1")

    assert "discard pending change" in rec.title
    assert "discard_me" in rec.squashed
    assert "never published" in rec.text.lower()


@pytest.mark.models("core")
def test_ward_delete_requires_a_connection(session: Session):
    """A queued delete cannot be made safe yet: `EMPTY_PART` is plaintext, so any host can
    construct a delete leaf for any entry_key, and uploading queued deletes would hand a host
    the power to delete anything. A write can wait in a queue; a delete cannot."""
    with pytest.raises(exceptions.TrezorFailure, match="connect"):
        ward.delete_entry(session, _APP, b"addr1", lambda _k: ward.Answer())


@pytest.mark.models("core")
def test_ward_set_entry_refuses_offline_and_names_the_queue_request(session: Session):
    """The online write no longer falls back to queueing, and the refusal says what to use.

    The fallback made ONE request mean two different things depending on state the host cannot
    see: sometimes a leaf came back, sometimes a receipt. A host could not tell from the request
    it sent whether its change had applied, which is the question the whole protocol exists to
    answer.
    """
    with pytest.raises(exceptions.TrezorFailure, match="WardQueueSetEntry"):
        ward.set_entry(
            session, _APP, b"addr1", b"v", lambda _k: ward.Answer()
        )


@pytest.mark.models("core")
def test_ward_get_entry_refuses_offline_and_names_the_queue_request(session: Session):
    """Same for the read, and here the refusal is also the security property.

    A device that pulled first and used its own copy whenever the pull failed would let a
    hostile host force an old value onto the screen by answering badly on purpose: fail the
    proof, get the cache. Now the local read is a request the host had to ask for by name.
    """
    with pytest.raises(exceptions.TrezorFailure, match="WardQueueGetEntry"):
        ward.get_entry(session, _APP, b"addr1", lambda _k: ward.Answer())


@pytest.mark.models("core")
def test_ward_queue_delete_discards_a_queued_change(session: Session):
    """The queue delete removes a change that was never published -- and nothing else."""
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"never_published")

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueDeleteEntry)
            + [m.ButtonRequest(name="ward_queue_delete_entry"), m.WardQueueDeleteAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        ack = ward.queue_delete_entry(session, _APP, b"addr1")

    assert ack.missing is None
    assert "discard queued change" in rec.title
    assert "never_published" in rec.squashed

    # and it is really gone, which the local read is the only way to see
    after = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "not kept offline" in after.title
    assert after.ack.missing is True


@pytest.mark.models("core")
def test_ward_queue_delete_of_nothing_is_reported_not_raised(session: Session):
    """"Nothing was queued" is an ANSWER. A host reconciling its own view of the queue will ask
    about a change that has already been published, and a Failure would make that ordinary case
    look like a fault. No screen either: a hold that always means "nothing happened" is one that
    gets approved without being read."""
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueDeleteEntry) + [m.WardQueueDeleteAck]
        )
        ack = ward.queue_delete_entry(session, _APP, b"never_queued")

    assert ack.missing is True


@pytest.mark.models("core")
def test_ward_queue_delete_will_not_touch_a_pinned_copy(session: Session):
    """A pinned read and a queued write live in the same store and are NOT the same question.

    "Do not publish this change" and "stop keeping this value on the device" cannot share one
    confirmation, so the queue delete reports a pinned record as missing and leaves it alone.
    `WardEraseCachedEntry` is the only way a pinned copy goes.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"pinned_value")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueDeleteEntry) + [m.WardQueueDeleteAck]
        )
        ack = ward.queue_delete_entry(session, _APP, b"addr1")
    assert ack.missing is True

    fresh = session.test_ctx.get_session()
    rec = _offline_read(fresh, b"addr1")
    assert "offline copy" in rec.title
    assert "pinned_value" in rec.squashed


# --- backing the queue up ------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_a_queued_change_round_trips_through_a_backup(session: Session):
    """Export a queued change, lose it, put it back -- and the device can tell it is its own.

    A queued change lives in ONE device's flash. Without this, a wipe loses a change the user
    confirmed and nothing can bring it back; with it, the host holds a blob it cannot forge.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"backed_up")

    backup = _offline_read(session.test_ctx.get_session(), b"addr1").ack
    assert backup.pending is True
    assert backup.value == b"backed_up"
    assert backup.app_id == _APP
    assert backup.identifier == b"addr1"
    assert len(backup.mac) == 32

    # lose it
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_delete_entry(session, _APP, b"addr1")
    assert _offline_read(session.test_ctx.get_session(), b"addr1").ack.missing is True

    # and put it back from the backup alone
    rec = _Recorded()
    fresh = session.test_ctx.get_session()
    with fresh.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueSetEntry)
            + [m.ButtonRequest(name="ward_queue_restore_entry"), m.WardQueueSetAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(fresh, on_page=rec.on_page).get()
        )
        ward.restore_queued_entry(fresh, backup)

    # Nothing is being replaced here -- the change was discarded first -- so the screen restores
    # rather than replaces. The replacing case is asserted separately below.
    assert "restore queued change" in rec.title
    assert "backed_up" in rec.squashed

    after = _offline_read(session.test_ctx.get_session(), b"addr1").ack
    assert after.pending is True
    assert after.value == b"backed_up"


@pytest.mark.models("core")
def test_ward_a_restored_change_still_publishes(session: Session):
    """The restore has to produce a record `flush_queue` can actually derive from, not just one
    that reads back. A backup that restores into something unpublishable would look correct on
    screen and lose the change at the only moment it matters."""
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"from_backup")

    backup = _offline_read(session.test_ctx.get_session(), b"addr1").ack

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_delete_entry(session, _APP, b"addr1")
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.restore_queued_entry(session, backup)

    _go_online(session, store)
    res = ward.flush_queue(session, ward.store_provider(store))
    assert res.remaining == 0
    value = unpack_content(
        open_content(_K_DATA, res.entry_key, "address", res.leaf.content.encrypted)
    )[1]
    assert value == b"from_backup"


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "corrupt",
    [
        pytest.param(lambda b: {"value": b.value + b"!"}, id="value"),
        pytest.param(lambda b: {"identifier": b"addr2"}, id="identifier"),
        pytest.param(lambda b: {"app_id": "OTHER"}, id="app_id"),
        pytest.param(lambda b: {"mac": bytes(32)}, id="mac"),
    ],
)
def test_ward_a_tampered_backup_is_refused_before_any_screen(session: Session, corrupt):
    """EVERY field the device would write back is inside the MAC.

    A blob travelling in the clear is a blob a host can edit, so a MAC over the path alone would
    authenticate a path while leaving the value free -- protection that looks like protection. Note
    the path and the key space are not editable at all: the device derives both and MACs what it
    derived, so an app_id or identifier edit changes the derived path and fails on that. The
    refusal happens BEFORE the confirmation, which `set_expected_responses` asserts by expecting no
    `ward_queue_entry` ButtonRequest: a screen for material that failed to authenticate teaches the
    user that the screen means nothing.

    A device with no app role asks to reveal first and is still refused after -- see
    `reveal_prefix`. That screen carries the request's own app_id and identifier and nothing from
    the backup, so what it endorses is the read, not the material that failed to authenticate.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"authentic")

    backup = _offline_read(session.test_ctx.get_session(), b"addr1").ack
    edited = {
        "app_id": backup.app_id,
        "identifier": backup.identifier,
        "value": backup.value,
        "mac": backup.mac,
    }
    edited.update(corrupt(backup))

    fresh = session.test_ctx.get_session()
    with fresh.test_ctx as ctx:
        ctx.set_expected_responses(reveal_prefix(m.WardQueueSetEntry) + [m.Failure])
        with pytest.raises(exceptions.TrezorFailure, match="authenticated"):
            ward.queue_set_entry(
                fresh,
                edited["app_id"],
                edited["identifier"],
                edited["value"],
                mac=edited["mac"],
            )


@pytest.mark.models("core")
def test_ward_a_pinned_copy_exports_no_intent_mac(session: Session):
    """A pinned read is not an intent: WARD already holds that value and there is nothing to
    re-queue. Returning a MAC for one would invite a restore that means nothing, so the fields come
    back for the host's records and the MAC does not."""
    store = WardTrie()
    _seed(session, store, b"addr1", b"pinned_value")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    backup = _offline_read(session.test_ctx.get_session(), b"addr1").ack
    assert backup.pending is None
    assert backup.value == b"pinned_value"
    assert backup.mac is None

    with pytest.raises(ValueError, match="no intent MAC"):
        ward.restore_queued_entry(session, backup)


@pytest.mark.models("core")
def test_ward_restoring_over_a_pending_change_names_both(session: Session):
    """A restore lands on a path that may already hold a later change, and the screen has to say so.

    The record on the device is what the user did LAST; the backup is older material by definition.
    Replacing one with the other silently is the failure the online write and the fresh queue write
    both design against -- both name what they replace -- and this is the path where it matters most,
    because the value arrives from a host rather than from the user.

    Note what the screen does NOT claim: which of the two is newer. No record stores a counter or a
    time, so it labels them by provenance and leaves the decision where it belongs.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"OLD_from_backup")

    backup = _offline_read(session.test_ctx.get_session(), b"addr1").ack

    # the user makes a later change at the same path
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"NEW_on_device")

    rec = _Recorded()
    fresh = session.test_ctx.get_session()
    with fresh.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueSetEntry)
            + [m.ButtonRequest(name="ward_queue_restore_entry"), m.WardQueueSetAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(fresh, on_page=rec.on_page).get()
        )
        ward.restore_queued_entry(fresh, backup)

    assert "replace pending change" in rec.title
    # BOTH values, told apart by where they came from
    assert "existing pending change" in rec.text.lower()
    assert "NEW_on_device" in rec.squashed
    assert "restored pending change" in rec.text.lower()
    assert "OLD_from_backup" in rec.squashed

    # and the backup is what is queued afterwards
    after = _offline_read(session.test_ctx.get_session(), b"addr1").ack
    assert after.value == b"OLD_from_backup"


@pytest.mark.models("core")
def test_ward_restoring_over_a_pinned_copy_says_which_it_is(session: Session):
    """A pinned copy is not a pending change, and the screen must not call it one.

    The two lead to different conclusions about what is being lost: a pinned copy is a value WARD
    already holds, so replacing it costs a local read; a pending change is one nobody has published,
    so replacing it costs the change itself.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"queued_then_backed_up")
    backup = _offline_read(session.test_ctx.get_session(), b"addr1").ack

    # replace what the device holds with a PINNED copy of a real entry at the same path
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_delete_entry(session, _APP, b"addr1")
    _seed(session, store, b"addr1", b"pinned_value")
    _pin(session, store, b"addr1", "ward_pin_cached_entry")

    rec = _Recorded()
    fresh = session.test_ctx.get_session()
    with fresh.test_ctx as ctx:
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(fresh, on_page=rec.on_page).get()
        )
        ward.restore_queued_entry(fresh, backup)

    assert "replace offline copy" in rec.title
    assert "existing offline copy" in rec.text.lower()
    assert "pinned_value" in rec.squashed


@pytest.mark.models("core")
def test_ward_queueing_a_longer_value_over_a_shorter_one(session: Session):
    """The same (app_id, identifier) again, with a value that no longer fits where the old one did.

    Worth its own test because the record is VARIABLE LENGTH and keyed by identity: the replacement
    reuses the slot, so a longer value means norcow rewriting the entry rather than patching it in
    place, and the byte budget sees the difference rather than the whole record. Values were address
    labels when this store was written; a wallet policy is an order of magnitude bigger, which is the
    case that never used to be exercised.

    The screen still has to name what is being replaced -- being longer is not a reason to skip that.
    """
    short = b"label"
    # policy-shaped: a descriptor template plus a few keys, well under MAX_VALUE_LEN but far past
    # what a label ever was
    long = (
        b"wsh(sortedmulti(3,"
        + b",".join(
            b"[abcd1234/48h/0h/0h/2h]xpub" + bytes(str(i), "ascii") * 60 for i in range(5)
        )
        + b"/**))"
    )
    assert 400 < len(long) < 1024  # a real 3-of-5, and inside MAX_VALUE_LEN

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", short)

    rec = _Recorded()
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueSetEntry)
            + [m.ButtonRequest(name="ward_queue_entry"), m.WardQueueSetAck]
        )
        ctx.set_input_flow(
            InputFlowConfirmAllWarnings(session, on_page=rec.on_page).get()
        )
        ward.queue_set_entry(session, _APP, b"addr1", long)

    # an update, and it says what it replaces
    assert "queue update" in rec.title
    assert short.decode() in rec.squashed

    # ...and the longer value is what the device holds now, whole
    after = _offline_read(session.test_ctx.get_session(), b"addr1").ack
    assert after.pending is True
    assert after.value == long

    # the slot was REUSED, not added to: a second entry still fits, which it would not if the
    # replacement had consumed a fresh slot's worth of budget on every write
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr2", long)
    assert _offline_read(session.test_ctx.get_session(), b"addr2").ack.value == long

    # and the first one is untouched by the second
    assert _offline_read(session.test_ctx.get_session(), b"addr1").ack.value == long


@pytest.mark.models("core")
def test_ward_a_value_past_the_cap_is_refused_and_the_old_one_survives(session: Session):
    """The other end of the same path: a value too long to store at all.

    A refusal has to leave the record it would have replaced exactly as it was. Failing AFTER
    clobbering the old value would be the worst outcome available here -- the user would have neither
    the change they asked for nor the one they had.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"keep_me")

    # MAX_VALUE_LEN is 1024; this is one past it, so it is rejected before any screen is shown
    with session.test_ctx as ctx:
        ctx.set_expected_responses(reveal_prefix(m.WardQueueSetEntry) + [m.Failure])
        with pytest.raises(exceptions.TrezorFailure, match="too large"):
            ward.queue_set_entry(session, _APP, b"addr1", b"x" * 1025)

    assert _offline_read(session.test_ctx.get_session(), b"addr1").ack.value == b"keep_me"


@pytest.mark.models("core")
def test_ward_replacing_an_entry_keeps_its_place_in_the_queue(session: Session):
    """add(1), add(2a), add(3), get(2a), add(2b) with 2b LONGER, set(2a) from the backup.

    WHAT THE SEQUENCE IS ABOUT. A record is variable length, so 2b cannot be patched over 2a -- on
    the blockwise models `flash_area_write_bytes` only succeeds when the new bytes are IDENTICAL, and
    on the bitwise ones only when every bit goes 1->0 -- so each rewrite appends a fresh norcow entry
    and marks the old one deleted. That is the layer below us reorganising itself, and the assertion
    here is that NONE of it reaches the queue: a record is addressed by its logical slot, so 2 keeps
    its place between 1 and 3 through both rewrites.

    The order is observable where it matters -- `flush_queue` publishes `next_unsent`, which walks
    slots in order -- so this checks the ORDER CHANGES ARE PUBLISHED IN, not just what is stored.
    """
    store = WardTrie()

    for ident, value in ((b"addr1", b"one"), (b"addr2", b"two_a"), (b"addr3", b"three")):
        with session.test_ctx as ctx:
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            ward.queue_set_entry(session, _APP, ident, value)

    # get(2a): the backup is taken while 2a is still what the device holds
    backup = _offline_read(session.test_ctx.get_session(), b"addr2").ack
    assert backup.value == b"two_a"

    # add(2b): longer than 2a, so nothing can be written over it in place
    two_b = b"two_b" + b"x" * 400
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr2", two_b)
    assert _offline_read(session.test_ctx.get_session(), b"addr2").ack.value == two_b

    # set(2a): the backup goes back, shorter again -- and again not in place
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.restore_queued_entry(session, backup)
    assert _offline_read(session.test_ctx.get_session(), b"addr2").ack.value == b"two_a"

    # the neighbours never moved and never changed
    assert _offline_read(session.test_ctx.get_session(), b"addr1").ack.value == b"one"
    assert _offline_read(session.test_ctx.get_session(), b"addr3").ack.value == b"three"

    # ORDERING: publication order is slot order, and slot order is insertion order. Two rewrites of
    # the middle record did not push it behind the one added after it.
    _go_online(session, store)
    published = []
    remaining = []
    for _ in range(3):
        res = ward.flush_queue(session, ward.store_provider(store))
        published.append(res.entry_key)
        remaining.append(res.remaining)

    assert published == [
        expected_entry_key(_K_PATH, _APP, ident)
        for ident in (b"addr1", b"addr2", b"addr3")
    ]
    assert remaining == [2, 1, 0]


# --- the compact record form ---------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_a_compact_record_reads_and_backs_up_like_any_other(session: Session):
    """`compact` keeps a HASH of the identity instead of the identity, and nothing above notices.

    Every request that touches a record already names the entry, so the device hashes what the caller
    named and finds the record by that. The screens still say which domain and key they are about --
    they read them from the REQUEST, which is where the full path gets them too -- and a backup still
    carries the identity, echoed from the request after the hash has agreed.
    """
    with session.test_ctx as ctx:
        ctx.set_expected_responses(
            reveal_prefix(m.WardQueueSetEntry)
            + [m.ButtonRequest(name="ward_queue_entry"), m.WardQueueSetAck]
        )
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"compact_value", compact=True)

    rec = _offline_read(session.test_ctx.get_session(), b"addr1")
    assert "compact_value" in rec.squashed
    assert _APP.lower() in rec.text.lower()  # the domain, from the request
    ack = rec.ack
    assert ack.pending is True
    assert ack.app_id == _APP
    assert ack.identifier == b"addr1"
    assert ack.value == b"compact_value"
    assert len(ack.mac) == 32

    # a DIFFERENT identity hashes elsewhere and finds nothing
    other = _offline_read(session.test_ctx.get_session(), b"addr2")
    assert other.ack.missing is True

    # the backup restores like any other, and may go back compact
    fresh = session.test_ctx.get_session()
    with fresh.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(fresh).get())
        ward.queue_delete_entry(fresh, _APP, b"addr1")
    with fresh.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(fresh).get())
        ward.restore_queued_entry(fresh, ack, compact=True)

    assert (
        _offline_read(session.test_ctx.get_session(), b"addr1").ack.value
        == b"compact_value"
    )


@pytest.mark.models("core")
def test_ward_a_compact_record_is_published_when_it_is_named(session: Session):
    """A compact record cannot be published by "take the next one" -- and it says so.

    The device holds a hash, and a hash does not become a keyed path -- nor can it say whose record it
    is, so an unnamed flush cannot even see it. A named one works, which is the whole contract of the
    compact form: the holder of the backup is the one who knows such a change is outstanding.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"needs_a_name", compact=True)

    _go_online(session, store)

    # UNNAMED, THERE IS NOTHING TO PUBLISH. A compact record is not enumerable -- that is the seven
    # bytes it saves -- so the queue looks empty to a flush that was not told which entry to take.
    empty = ward.flush_queue(session, ward.store_provider(store))
    assert empty.remaining == 0
    assert empty.entry_key == b""

    res = ward.flush_queue(
        session, ward.store_provider(store), app_id=_APP, identifier=b"addr1"
    )
    assert res.remaining == 0
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr1")
    value = unpack_content(
        open_content(_K_DATA, res.entry_key, "address", res.leaf.content.encrypted)
    )[1]
    assert value == b"needs_a_name"


@pytest.mark.models("core")
def test_ward_naming_an_entry_publishes_that_one_not_the_first(session: Session):
    """The named flush is not only for compact records: it picks the entry, whatever form it is in.

    Worth pinning because the unnamed path publishes in slot order, and a host with several queued
    changes and one backup in hand needs to be able to say which.
    """
    store = WardTrie()

    for ident, value in ((b"addr1", b"first"), (b"addr2", b"second")):
        with session.test_ctx as ctx:
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            ward.queue_set_entry(session, _APP, ident, value)

    _go_online(session, store)

    res = ward.flush_queue(
        session, ward.store_provider(store), app_id=_APP, identifier=b"addr2"
    )
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr2")
    # the other one is still waiting, and is what an unnamed flush takes
    assert res.remaining == 1
    res = ward.flush_queue(session, ward.store_provider(store))
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr1")
    assert res.remaining == 0


@pytest.mark.models("core")
def test_ward_both_record_forms_share_one_store(session: Session):
    """A full and a compact record of different entries, side by side.

    Both are found by identity, both are counted as pending, and neither shadows the other -- the
    lookup asks for both names at once, so which form an entry happens to be in never has to be known
    by anything above the store.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"stored_full")
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr2", b"stored_compact", compact=True)

    assert (
        _offline_read(session.test_ctx.get_session(), b"addr1").ack.value
        == b"stored_full"
    )
    assert (
        _offline_read(session.test_ctx.get_session(), b"addr2").ack.value
        == b"stored_compact"
    )

    # `remaining` counts what can be published UNPROMPTED, so the compact one is not in it: only its
    # holder knows it is there, and only a named flush can hand it over.
    _go_online(session, store)
    res = ward.flush_queue(session, ward.store_provider(store))
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr1")
    assert res.remaining == 0

    res = ward.flush_queue(
        session, ward.store_provider(store), app_id=_APP, identifier=b"addr2"
    )
    assert res.entry_key == expected_entry_key(_K_PATH, _APP, b"addr2")


@pytest.mark.models("core")
def test_ward_rewriting_an_entry_compactly_replaces_it(session: Session):
    """Changing form must take over the slot, not leave the old form behind.

    Two records for one entry under two names would both be findable, and which one a read returned
    would depend on slot order -- so a value the user replaced could come back later.
    """
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"was_full")

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"now_compact", compact=True)

    assert (
        _offline_read(session.test_ctx.get_session(), b"addr1").ack.value
        == b"now_compact"
    )

    # ...and back to the full form, still one record
    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"full_again")
    assert (
        _offline_read(session.test_ctx.get_session(), b"addr1").ack.value
        == b"full_again"
    )

    # one slot used: nineteen more entries still fit
    for i in range(19):
        with session.test_ctx as ctx:
            ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
            ward.queue_set_entry(session, _APP, b"fill%d" % i, b"v", compact=True)
    assert (
        _offline_read(session.test_ctx.get_session(), b"addr1").ack.value
        == b"full_again"
    )


@pytest.mark.models("core")
def test_ward_a_named_flush_may_hand_over_the_same_change_twice(session: Session):
    """The offered flag stops the UNNAMED loop repeating itself; a caller naming an entry overrides it.

    This is the way back for a change offered by a session that then dropped: the claim ledger went
    with the session, so no reconcile will settle it, and refusing to re-offer would strand it. A
    re-send costs a round trip; refusing costs the change.
    """
    store = WardTrie()

    with session.test_ctx as ctx:
        ctx.set_input_flow(InputFlowConfirmAllWarnings(session).get())
        ward.queue_set_entry(session, _APP, b"addr1", b"offered_twice")

    _go_online(session, store)

    first = ward.flush_queue(
        session, ward.store_provider(store), app_id=_APP, identifier=b"addr1"
    )
    again = ward.flush_queue(
        session, ward.store_provider(store), app_id=_APP, identifier=b"addr1"
    )

    assert first.entry_key == again.entry_key
    value = unpack_content(
        open_content(_K_DATA, again.entry_key, "address", again.leaf.content.encrypted)
    )[1]
    assert value == b"offered_twice"

    # ...while the unnamed loop still considers it handed over
    assert ward.flush_queue(session, ward.store_provider(store)).remaining == 0


# --- the two continuity rules -------------------------------------------------------------
#
# Naming BOTH ends of the WM's head nonce turns the attestation into a statement about the
# transition OCCURRENCE, and that buys the device two checks against the head it last saw. They
# are the only means it has of catching a WM whose nonce register moved incoherently -- the
# failure the operator obligation in `apps/ward/cas` is about -- so they are worth pinning at the
# wire rather than only in the mock.


@pytest.mark.models("core")
def test_ward_refuses_an_attestation_that_consumed_another_nonce(session: Session):
    """R1, THE ADVANCE. If the WM advanced out of the head this device is holding, the nonce it
    consumed must be the one this device latched for that head.

    This is how a device learns that the authorisation IT minted is the one that was spent, and
    not that some other occurrence of the same transition landed. Roots repeat and a revert
    re-creates an older pair on purpose, so "the same transition" is genuinely ambiguous without
    it.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)
    _attest(session, wm, store)  # the device now holds (counter, root, nonce)

    target = store.counter + 1
    root = store.root()
    latched = wm.head_nonce(_WARD_ID)
    minted = bytes([0x5F]) * 32

    # A GENUINE WM SIGNATURE over a step out of the device's head -- but naming some other nonce
    # as the one it consumed. Nothing else about it is wrong.
    ack = ward.sync(session)
    wrong = bytes([0xC7]) * 32
    assert wrong != latched
    sig = wm.sign(
        ack.ward_id, ack.nonce, store.counter, root, wrong, target, root, minted, _T0 + target
    )
    with pytest.raises(exceptions.TrezorFailure, match="did not consume"):
        ward.ingest_attestation(
            session, store.counter, root, target, root, sig, wrong, minted, _T0 + target
        )

    # ...and the same step naming the RIGHT one is taken, so the refusal above is about the nonce
    # and not about anything else in the message.
    ack = ward.sync(session)
    sig = wm.sign(
        ack.ward_id, ack.nonce, store.counter, root, latched, target, root, minted, _T0 + target
    )
    ward.ingest_attestation(
        session, store.counter, root, target, root, sig, latched, minted, _T0 + target
    )


@pytest.mark.models("core")
def test_ward_refuses_a_nonce_that_moved_while_the_head_did_not(session: Session):
    """R2, THE STANDSTILL -- the restore detector, and the one case the device can catch alone.

    Every transition advances the counter by exactly one, so a head that did not move accepted
    nothing and cannot have rotated its nonce. A different nonce on an unmoved head therefore
    means the register moved without a transition: a backup restore, a failover onto a stale
    replica, a fork.

    Modelled as the most likely shape of it -- a register restored to exactly the head this
    device is standing on, which is what an operator recovering a WM would most often produce.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)
    _attest(session, wm, store)

    counter, root = store.counter, store.root()
    before = wm.head_nonce(_WARD_ID)

    # THE HEAD IS PUT BACK EXACTLY WHERE IT IS, which is what a restore onto the current head
    # looks like. The counter and the root do not move; the nonce does, because a correct restore
    # must never re-issue a superseded one.
    wm.install_unauthenticated(
        _WARD_ID,
        counter,
        root,
        _T0 + counter,
        *_step_into(store, counter, root),
        restore=True,
    )
    assert wm.head(_WARD_ID)[:2] == (counter, root)
    assert wm.head_nonce(_WARD_ID) != before

    ack = ward.sync(session)
    fc, fr, fhn, tc, tr, hn, ts, sig = wm.attest(ack.ward_id, ack.nonce)
    with pytest.raises(exceptions.TrezorFailure, match="without the head moving"):
        ward.ingest_attestation(session, fc, fr, tc, tr, sig, fhn, hn, ts)


@pytest.mark.models("core")
def test_ward_takes_an_unmoved_head_that_kept_its_nonce(session: Session):
    """The other side of R2: re-confirming the same head is an ordinary, frequent thing.

    A host that syncs twice without writing gets the same attestation content back, and the rule
    must not make that an error -- it only bites when the nonce moved without the head.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)
    _attest(session, wm, store)
    _attest(session, wm, store)  # again, nothing moved
    assert ward.sync(session) is not None


@pytest.mark.models("core")
def test_ward_refuses_an_attested_head_carrying_the_enrolment_nonce(session: Session):
    """`NO_HEAD_NONCE` is what `head_init_sig` is signed under, and NOTHING ELSE.

    A WM that accepts an enrolment draws a real `N0` before it attests anything, so no live head
    ever carries the constant. The device enforces that, and the reason is worth stating as the
    attack: `head_init_sig` is a fixed statement and is not secret, so whoever holds one can
    re-enrol a WM that lost everything. If enrolment left the head at a CONSTANT, that replay
    would land the fresh WM on exactly the predecessor triple the first write was authorised
    against -- `(0, EMPTY_ROOT, NO_HEAD_NONCE)` -- and a retained authorisation for it would be
    live again. Genesis is where every wallet starts and where any drained wallet returns, so
    that is not an obscure corner.
    """
    store = WardTrie()
    _seed(session, store, b"addr1", b"v")
    wm = _wm_for(store)
    _attest(session, wm, store)

    target = store.counter + 1
    root = store.root()
    ack = ward.sync(session)

    # a genuine WM signature over a well-formed step -- whose new head carries the constant
    sig = wm.sign(
        ack.ward_id,
        ack.nonce,
        store.counter,
        root,
        wm.head_nonce(_WARD_ID),
        target,
        root,
        NO_HEAD_NONCE,
        _T0 + target,
    )
    with pytest.raises(exceptions.TrezorFailure, match="enrolment nonce"):
        ward.ingest_attestation(
            session,
            store.counter,
            root,
            target,
            root,
            sig,
            wm.head_nonce(_WARD_ID),
            NO_HEAD_NONCE,
            _T0 + target,
        )


@pytest.mark.models("core")
def test_ward_enrolment_draws_a_live_nonce(session: Session):
    """The connect-mode enrolment flow end to end, on a WM that has never seen this wallet.

    `WardSyncAck` carries the device's `head_init_sig`; the WM verifies it, draws `N0`, and
    attests genesis. Only then does the device hold a nonce it can authorise a write against --
    which is why enrolment cannot be folded into the first write, and why nothing here has to be.
    """
    store = WardTrie()
    wm = _wm_for(store)

    ack = ward.sync(session)
    assert ack.head_init_sig is not None
    assert ack.counter == 0

    fc, fr, fhn, tc, tr, hn, ts, sig = wm.attest_head(
        ack.ward_id, ack.nonce, 0, None, ack.head_init_sig
    )
    # GENESIS CONSUMES NOTHING, so both ends carry the same nonce -- but it is a real one.
    assert fhn == hn != NO_HEAD_NONCE
    assert (fc, tc) == (0, 0)

    ward.ingest_attestation(session, fc, fr, tc, tr, sig, fhn, hn, ts)
    ward.reconcile(session, None)

    # and the device can now write, quoting the nonce it just learned
    res, _rec = _write(
        session,
        store,
        lambda p: ward.set_entry(session, _APP, b"addr1", b"v", p),
        "ward_set_entry",
    )
    ward.apply(store, res)
    wm.advance(
        ack.ward_id,
        *_step_into(store, res.counter, store.root()),
        res.counter,
        store.root(),
        res.wm_sig,
        _T0 + res.counter,
    )
    assert wm.head(ack.ward_id)[:2] == (res.counter, store.root())
