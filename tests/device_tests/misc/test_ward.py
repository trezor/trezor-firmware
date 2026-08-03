"""Device tests for the WARD pull update round
(queue_update -> perform_update -> confirmed_by_wm).

queue_update stores an intent behind a trusted confirm screen (approved here via
the debuglink); perform_update makes the device PULL the proof from the host
WARDTree (served by ward_proof_callback) and compute the candidate; confirmed_by_wm
installs it. The WARD Manager's final attestation is signed locally with the debug
WM key (ward_mgr_emu.DEBUG_QM_SEED), accepted only on debug firmware.
"""

import pytest

from trezorlib import btc, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...device_handler import BackgroundDeviceHandler
from ...ward_mgr_emu import device_ward_keys, sign_ward_update, sign_wm_attestation

_APP = "bitcoin"  # capability principal == queried domain for these tests

# The host tree must use the DEVICE's WARD keys (reproduced from the known test
# seed) so its entry_keys/leaf commits match the device's and its proofs verify.
_K_INDEX, _K_DATA = device_ward_keys()


def _tree() -> WARDTree:
    """Host WARDTree keyed by the device's K_index/K_data."""
    return WARDTree(_K_INDEX, _K_DATA)


def _apply_device_leaf(tree: WARDTree, perform_result: tuple) -> None:
    """Keep the host tree in sync with the device after a write: store the exact
    encrypted leaf blob the device returned in WARDPerformUpdateAck (its nonce is
    random, so the host must NOT re-encrypt or roots would diverge). Trailing 5
    fields of perform_result are (entry_key, entry_type, nonce, tag, ct); empty ct
    means DELETE."""
    ek, entry_type, nonce, tag, ct = perform_result[5:10]
    if ct:
        tree.set_leaf(ek, nonce, tag, ct, entry_type or "address")
    elif ek is not None:
        tree.del_leaf(ek)


def _lookup_membership(session: Session, tree: WARDTree, address: bytes):
    """Membership WARDLookup with the new signature (leaf blob + proof)."""
    blob = tree.leaf_blob(_APP, address)
    assert blob is not None, f"{address!r} not in tree"
    return ward.lookup(
        session,
        _APP,
        address,
        tree.get_proof(_APP, address),
        nonce=blob[0],
        tag=blob[1],
        ct=blob[2],
    )

ENTRIES = {
    b"alice": b"data_alice",
    b"bob": b"data_bob",
    b"carol": b"data_carol",
    b"dave": b"data_dave",
}


class InMemoryEvoluStore:
    """Minimal host-side store for the attested WARD root blob."""

    def __init__(self) -> None:
        self.root: bytes | None = None
        self.counter = 0
        self.root_mac: bytes | None = None

    def get_root(self) -> tuple[bytes | None, int, bytes | None]:
        return self.root, self.counter, self.root_mac

    def put_root(self, root: bytes | None, counter: int, root_mac: bytes | None) -> None:
        self.root = root
        self.counter = counter
        self.root_mac = root_mac


class InMemoryWardManager:
    """Debug-key WM stub used by the firmware device tests."""

    @staticmethod
    def sign_attestation(ward_id: bytes, nonce: bytes, counter: int, mac: bytes) -> bytes:
        return sign_wm_attestation(nonce, counter, mac, ward_id)

    @staticmethod
    def sign_final(ward_id: bytes, counter: int, mac: bytes) -> bytes:
        return sign_ward_update(counter, mac, ward_id)


class WardHostHarness:
    """In-memory host harness for WARD end-to-end tests.

    Keeps the authenticated Merkle state in WARDTree and the attested
    (root, counter, root_mac) blob in the Evolu-like store.
    """

    def __init__(self) -> None:
        self.tree = _tree()
        self.store = InMemoryEvoluStore()
        self.wm = InMemoryWardManager()
        self.queue: list[tuple[bytes, bytes]] = []

    def bootstrap_device(self, session: Session) -> tuple[int, bytes | None, bytes | None, bytes | None]:
        root, counter, root_mac = self.store.get_root()
        nonce, ward_id = ward.sync(session)
        assert ward_id is not None
        _pending, wallet_id = ward.list_pending(session)
        assert wallet_id is not None
        mac_for_sig = root_mac if root_mac is not None else ward.ZERO_MAC
        sig = self.wm.sign_attestation(ward_id, nonce, counter, mac_for_sig)
        ward.ingest_attestation(session, counter, root_mac, sig)
        out_counter, out_root, out_root_mac = ward.reconcile(session, root)
        return out_counter, out_root, wallet_id, out_root_mac

    def lookup(self, session: Session, address: bytes) -> bytes | None:
        if self.tree.get_counter(_APP, address):
            value = self.tree.get_value(_APP, address)
            valid, membership, _counter, _wallet_id = _lookup_membership(
                session, self.tree, address
            )
            assert valid and membership
            return value

        proof, witness_entry_key, witness_commit = (
            self.tree.get_nonmembership_proof(_APP, address)
        )
        valid, membership, _counter, _wallet_id = ward.lookup(
            session, _APP,
            address,
            proof,
            witness_entry_key=witness_entry_key,
            witness_commit=witness_commit,
        )
        assert valid and not membership
        return None

    def set_value(self, session: Session, address: bytes, value: bytes | None) -> int:
        self.bootstrap_device(session)

        # Queue the intent (trusted confirm), then let the device pull the proof
        # for the current tree at perform time and WM-sign the candidate.
        old_value = (
            self.tree.get_value(_APP, address) if self.tree.get_counter(_APP, address) else b""
        )
        pending_id = _queue_update(session, address, old_value, value or b"")

        res = _perform(session, self.tree, pending_id)
        c_counter, _root_t, mac_t, wallet_id, ward_id = res[:5]
        mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
        assert ward_id is not None
        sig = self.wm.sign_final(ward_id, c_counter, mac_for_sig)
        counter, new_root, _wallet_id, root_mac = ward.confirmed_by_wm(
            session, c_counter, mac_t, sig, pending_id
        )

        # Store the device's own encrypted leaf blob (random nonce) so the host
        # tree tracks the device's authenticated root exactly.
        _apply_device_leaf(self.tree, res)

        expected_root = None if self.tree.is_empty() else self.tree.get_root_hash()
        assert new_root == expected_root
        self.store.put_root(new_root, counter, root_mac)
        return counter

    def enqueue_set(self, address: bytes, value: bytes | None) -> None:
        self.queue.append((address, value or b""))

    def drain_queue(self, session: Session) -> int:
        applied = 0
        while self.queue:
            address, value = self.queue.pop(0)
            self.set_value(session, address, value or None)
            applied += 1
        return applied


def _make_tree() -> WARDTree:
    tree = _tree()
    for addr, val in ENTRIES.items():
        tree.insert(_APP, addr, val, counter=1)
    return tree


def _seed_device(session: Session, tree: WARDTree) -> int:
    """Install the host tree's root on the device (debug injection) and return the
    device counter it now sits at."""
    counter, _root, _wid, _mac = ward.debug_set_root(session, tree.get_root_hash())
    return counter


def _sync_device(
    session: Session,
    counter: int,
    root: bytes | None,
    root_mac: bytes | None,
) -> tuple[int, bytes | None, bytes | None, bytes | None]:
    nonce, ward_id = ward.sync(session)
    assert ward_id is not None
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    mac_for_sig = root_mac if root_mac is not None else ward.ZERO_MAC
    sig = sign_wm_attestation(nonce, counter, mac_for_sig, ward_id)
    ward.ingest_attestation(session, counter, root_mac, sig)
    out_counter, out_root, out_root_mac = ward.reconcile(session, root)
    return out_counter, out_root, wallet_id, out_root_mac


def _queue_update(
    session: Session,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
) -> int:
    """Queue an edit INTENT through the trusted confirm screen (approve it via the
    debuglink). Returns pending_id. Strict model: NO candidate counter is derived
    at queue time."""
    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: ward.queue_update(s, _APP, address, old_value, new_value),
            )
            dev.debuglink().press_yes()
            pending_id, _wallet_id = dev.result()
    assert pending_id is not None
    return pending_id


def _perform(
    session: Session,
    tree: WARDTree,
    pending_id: int,
) -> tuple[int, bytes | None, bytes | None, bytes | None, bytes | None]:
    """WARDPerformUpdate: the device derives counter_T (strict model) and pulls the
    proof for `tree` (current, pre-edit state) via ward_proof_callback, then computes
    the candidate. No user interaction. Returns
    (counter_T, root_T, mac_T, wallet_id, ward_id)."""
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    return ward.perform_update(session, pending_id)


def _perform_and_finalize(
    session: Session,
    tree: WARDTree,
    pending_id: int,
) -> tuple[int, bytes | None, bytes | None, bytes | None]:
    """perform_update -> WM-sign -> confirmed_by_wm. Returns the confirm result.
    Also stores the device-returned leaf blob into `tree` so the host stays in sync
    with the device's authenticated root (the device is the encryptor)."""
    res = _perform(session, tree, pending_id)
    c_counter, _root_t, mac_t, _wallet_id, ward_id = res[:5]
    mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
    assert ward_id is not None
    sig = sign_ward_update(c_counter, mac_for_sig, ward_id)
    confirmed = ward.confirmed_by_wm(session, c_counter, mac_t, sig, pending_id)
    _apply_device_leaf(tree, res)
    return confirmed


def _edit(
    session: Session,
    tree: WARDTree,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
) -> tuple[int, bytes | None, bytes | None, bytes | None, int]:
    """Full pull update round for one edit. Returns
    (counter, new_root, wallet_id, root_mac, pending_id)."""
    pending_id = _queue_update(session, address, old_value, new_value)
    counter, new_root, wallet_id, root_mac = _perform_and_finalize(
        session, tree, pending_id
    )
    return counter, new_root, wallet_id, root_mac, pending_id


def _pending_addresses(session: Session) -> list[bytes]:
    """The addresses currently queued as pending edits (multi-slot)."""
    addresses, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    return addresses


@pytest.mark.models("core")
def test_ward_update(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    counter, new_root, wallet_id, root_mac, _pid = _edit(
        session, tree, b"alice", ENTRIES[b"alice"], b"data_alice_v2"
    )

    # _edit already synced the device's leaf blob into `tree`.
    assert counter == new_counter
    assert new_root == tree.get_root_hash()
    assert root_mac is not None
    assert wallet_id is not None and len(wallet_id) == 20


@pytest.mark.models("core")
def test_ward_insert(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    counter, new_root, _wid, _mac, _pid = _edit(
        session, tree, b"erin", b"", b"data_erin"
    )

    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_delete(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    counter, new_root, _wid, _mac, _pid = _edit(
        session, tree, b"alice", ENTRIES[b"alice"], b""
    )

    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_counter_advances_only_at_finalize(session: Session) -> None:
    """queue_update + perform_update must NOT advance the device counter; only the
    WM confirmation does."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    pending_id = _queue_update(
        session, b"alice", ENTRIES[b"alice"], b"data_alice_v2"
    )
    c_counter, _root_t, mac_t, _wallet_id, ward_id, *_ = _perform(session, tree, pending_id)

    # After perform, the authenticated root/counter are still the pre-edit ones.
    valid, membership, dev_counter, _wid = _lookup_membership(session, tree, b"alice")
    assert valid and membership
    assert dev_counter == counter0  # not advanced yet

    sig = sign_ward_update(c_counter, mac_t, ward_id)
    counter, _new_root, _wid, _root_mac = ward.confirmed_by_wm(
        session, c_counter, mac_t, sig, pending_id
    )
    assert counter == new_counter  # advanced now


@pytest.mark.models("core")
def test_ward_finalize_bad_signature_rejected(session: Session) -> None:
    tree = _make_tree()
    _seed_device(session, tree)

    pending_id = _queue_update(
        session, b"alice", ENTRIES[b"alice"], b"data_alice_v2"
    )
    c_counter, _root_t, mac_t, _wallet_id, _ward_id, *_ = _perform(session, tree, pending_id)

    bad_sig = bytes(64)  # not a valid WM signature
    with pytest.raises(TrezorFailure):
        ward.confirmed_by_wm(session, c_counter, mac_t, bad_sig, pending_id)


@pytest.mark.models("core")
def test_ward_second_set_entry_queues_distinct_pending_id(session: Session) -> None:
    """Multi-slot queue: a second queue_update while one is pending is accepted and
    gets its own pending_id (the old depth-1 rejection no longer applies)."""
    tree = _make_tree()
    _seed_device(session, tree)

    pid1 = _queue_update(session, b"alice", ENTRIES[b"alice"], b"data_alice_v2")
    pid2 = _queue_update(session, b"bob", ENTRIES[b"bob"], b"data_bob_v2")
    assert pid1 != pid2

    # Both are queued simultaneously.
    addresses, _wallet_id = ward.list_pending(session)
    assert set(addresses) == {b"alice", b"bob"}


# ---------------------------------------------------------------------------
# Sync round (bootstrap/refresh): InitSyncRound -> IngestAttestation -> MergeState
# ---------------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_bootstrap_adopts_attested_root(session: Session) -> None:
    """A full sync round with a debug WM-signed attestation adopts the host root."""
    tree = _make_tree()
    root = tree.get_root_hash()

    # The device's own MAC over (root, counter) is what the attestation's mac must
    # equal; obtain it by seeding once (debug) and reading the returned root_mac.
    counter, _r, _wid, mac = ward.debug_set_root(session, root)

    # Now drive a real sync round at the next counter, re-adopting the same root.
    out_counter, new_root, _wid, _rm = _sync_device(session, counter, root, mac)
    assert out_counter == counter
    assert new_root == root


@pytest.mark.models("core")
def test_ward_ingest_bad_signature_rejected(session: Session) -> None:
    tree = _make_tree()
    counter, _r, _wid, mac = ward.debug_set_root(session, tree.get_root_hash())

    nonce, ward_id = ward.sync(session)
    assert ward_id is not None
    valid_sig = sign_wm_attestation(nonce, counter, mac, ward_id)
    bad_sig = bytes([valid_sig[0] ^ 0x01]) + valid_sig[1:]
    with pytest.raises(TrezorFailure):
        ward.ingest_attestation(session, counter, mac, bad_sig)


@pytest.mark.models("core")
def test_ward_ingest_rollback_rejected(session: Session) -> None:
    """An attested counter below the device floor is rejected (anti-rollback)."""
    tree = _make_tree()
    # advance the device to counter 2
    ward.debug_set_root(session, tree.get_root_hash())
    counter, _r, _wid, mac = ward.debug_set_root(session, tree.get_root_hash())
    assert counter >= 2

    # Attest a stale counter 1 < counter_loc with a correctly-signed attestation.
    nonce, ward_id = ward.sync(session)
    assert ward_id is not None
    sig = sign_wm_attestation(nonce, 1, mac, ward_id)
    with pytest.raises(TrezorFailure):
        ward.ingest_attestation(session, 1, mac, sig)


@pytest.mark.models("core")
def test_ward_catchup_adopts_reconstructable_root(session: Session) -> None:
    """Catch-up happy path: the shared state advances to a new (counter, root) and
    this device syncs up to it. Because the host-supplied root reconstructs to the
    WM-attested mac, reconcile adopts it and the device's counter moves forward.

    Simulates a multi-device wallet: a peer commits an update (modelled by the
    debug root injection, which returns the device MAC the WM stores alongside the
    head), while this device is one round behind and catches up over sync.
    """
    # Round 1: this device is synced at an older head (counter 1, root0).
    tree = _make_tree()
    root0 = tree.get_root_hash()
    counter0, _r, _wid, mac0 = ward.debug_set_root(session, root0)
    synced0, adopted0, _wid, _rm = _sync_device(session, counter0, root0, mac0)
    assert synced0 == counter0
    assert adopted0 == root0

    # A peer advances the shared head to a new root at the next counter.
    tree.insert(_APP, b"erin", b"data_erin", counter=1)
    root1 = tree.get_root_hash()
    assert root1 != root0
    counter1, _r, _wid, mac1 = ward.debug_set_root(session, root1)
    assert counter1 > counter0

    # Catch up: a full sync round adopts the advanced, reconstructable head.
    synced1, adopted1, _wid, _rm = _sync_device(session, counter1, root1, mac1)
    assert synced1 == counter1
    assert adopted1 == root1


@pytest.mark.models("core")
def test_ward_catchup_rejects_unreconstructable_root(session: Session) -> None:
    """Catch-up fail path: the WM attests (counter, mac) for one root, but the host
    serves a *different* root that does not reconstruct to that mac. reconcile must
    refuse to adopt the unauthenticated head rather than install it.
    """
    tree = _make_tree()
    tree.insert(_APP, b"erin", b"data_erin", counter=1)
    root = tree.get_root_hash()
    counter, _r, _wid, mac = ward.debug_set_root(session, root)

    # The WM signs a valid freshness attestation binding `mac` to `root@counter`.
    nonce, ward_id = ward.sync(session)
    assert ward_id is not None
    sig = sign_wm_attestation(nonce, counter, mac, ward_id)
    ward.ingest_attestation(session, counter, mac, sig)

    # The host serves a root the attested mac does not commit to: it cannot be
    # reconstructed against the attestation, so reconcile must reject it.
    bogus_tree = _make_tree()
    bogus_tree.insert(_APP, b"mallory", b"data_mallory", counter=1)
    bogus_root = bogus_tree.get_root_hash()
    assert bogus_root != root
    with pytest.raises(TrezorFailure):
        ward.reconcile(session, bogus_root)


@pytest.mark.models("core")
def test_ward_e2e_in_memory_store_lookup_modify(session: Session) -> None:
    """End-to-end WARD scenario driven through an in-memory Evolu/WM host harness."""
    host = WardHostHarness()

    # Fresh wallet: bootstrap empty state, then prove a missing address is absent.
    counter, root, _wallet_id, root_mac = host.bootstrap_device(session)
    assert counter == 0
    assert root is None
    assert root_mac is None
    assert host.lookup(session, b"adr1") is None

    # INSERT -> membership lookup.
    host.set_value(session, b"adr1", b"Petr_adr1_v0")
    assert host.lookup(session, b"adr1") == b"Petr_adr1_v0"

    # UPDATE -> membership lookup reflects the new label.
    host.set_value(session, b"adr1", b"Petr_adr1_v1")
    assert host.lookup(session, b"adr1") == b"Petr_adr1_v1"

    # Queue one offline change and drain it while online.
    host.enqueue_set(b"adr2", b"Petr_adr2_v0")
    assert host.drain_queue(session) == 1
    assert host.lookup(session, b"adr2") == b"Petr_adr2_v0"

    # DELETE -> non-membership lookup.
    host.set_value(session, b"adr1", None)
    assert host.lookup(session, b"adr1") is None


# ---------------------------------------------------------------------------
# On-device path: Trezor App (getAddress) -> Core(appId) -> WARD lookup.
# The verified label replaces the account name on the trusted address screen.
# Requires driving the show_address confirmation UI; captured here as the
# intended flow and skipped until wired to the standard input-flow handling.
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="needs emulator + show_address input-flow handling")
@pytest.mark.models("core")
def test_ward_get_address_label(session: Session) -> None:
    path = parse_path("m/44h/0h/0h/0/0")

    # 1. Learn the address, then build a WARD tree keyed by the address string.
    address = btc.get_address(session, "Bitcoin", path)
    tree = WARDTree()
    tree.insert(_APP, address.encode(), b"alice.btc", counter=1)

    # 2. Install that authenticated root on the device (debug seed).
    ward.debug_set_root(session, tree.get_root_hash())

    # 3. Request the address again with a WARD membership proof; the device
    #    verifies it via Core -> WARD and shows "alice.btc" as the account label.
    result = btc.get_authenticated_address(
        session,
        "Bitcoin",
        path,
        show_display=True,
        ward_value=b"alice.btc",
        ward_proof=tree.get_proof(_APP, address.encode()),
        ward_counter=1,
    )
    assert result.address == address


# ---------------------------------------------------------------------------
# Pending-queue deletion: after a write round finalizes, the queued candidate
# must be dropped (confirm_commit -> queue_drop), regardless of the operation.
# Each test asserts the queue is empty before, holds the address mid-round, and
# is empty again after finalize.
# ---------------------------------------------------------------------------


@pytest.mark.models("core")
def test_ward_pending_queue_cleared_after_insert(session: Session) -> None:
    tree = _make_tree()
    _seed_device(session, tree)

    assert _pending_addresses(session) == []
    pid = _queue_update(session, b"erin", b"", b"data_erin")
    assert _pending_addresses(session) == [b"erin"]

    _perform_and_finalize(session, tree, pid)
    assert _pending_addresses(session) == []


@pytest.mark.models("core")
def test_ward_pending_queue_cleared_after_update(session: Session) -> None:
    tree = _make_tree()
    _seed_device(session, tree)

    assert _pending_addresses(session) == []
    pid = _queue_update(session, b"alice", ENTRIES[b"alice"], b"data_alice_v2")
    assert _pending_addresses(session) == [b"alice"]

    _perform_and_finalize(session, tree, pid)
    assert _pending_addresses(session) == []


@pytest.mark.models("core")
def test_ward_pending_queue_cleared_after_delete(session: Session) -> None:
    tree = _make_tree()
    _seed_device(session, tree)

    assert _pending_addresses(session) == []
    pid = _queue_update(session, b"alice", ENTRIES[b"alice"], b"")
    assert _pending_addresses(session) == [b"alice"]

    _perform_and_finalize(session, tree, pid)
    assert _pending_addresses(session) == []


@pytest.mark.models("core")
def test_ward_pending_queue_cleared_after_update_to_current_value(
    session: Session,
) -> None:
    """Updating a leaf to the value it already holds is still a real edit (the
    leaf counter advances, so the root changes); the queue must clear afterwards."""
    tree = _make_tree()
    _seed_device(session, tree)

    assert _pending_addresses(session) == []
    pid = _queue_update(
        session, b"alice", ENTRIES[b"alice"], ENTRIES[b"alice"]  # unchanged value
    )
    assert _pending_addresses(session) == [b"alice"]

    _perform_and_finalize(session, tree, pid)
    assert _pending_addresses(session) == []


@pytest.mark.models("core")
def test_ward_rejected_finalize_keeps_pending_queue(session: Session) -> None:
    """A finalize with an untrusted WM signature is rejected, and the committed
    candidate MUST survive. The rejection concerns the external attestation, not
    the device-authenticated candidate, so the host can re-request a valid
    signature and retry -- rather than rebuild the whole edit. Dropping here would
    turn a transient/external signature failure into lost work (and let a bad
    confirm_commit grief in-flight edits). A subsequent valid finalize completes
    the same candidate."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    pending_id = _queue_update(
        session, b"alice", ENTRIES[b"alice"], b"data_alice_v2"
    )
    res = _perform(session, tree, pending_id)
    c_counter, _root_t, mac_t, _wallet_id, ward_id = res[:5]
    assert ward_id is not None
    assert _pending_addresses(session) == [b"alice"]

    # A well-formed signature from an untrusted key: passes the counter/mac match
    # check, then fails the WM attestation check -- confirmed_by_wm raises BEFORE
    # queue_drop, so the candidate must remain.
    mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
    bad_sig = sign_ward_update(
        c_counter, mac_for_sig, ward_id, qm_seed=b"NOT THE WARD MANAGER DEBUG KEY!!"
    )
    with pytest.raises(
        TrezorFailure, match="WM final attestation verification failed"
    ):
        ward.confirmed_by_wm(session, c_counter, mac_t, bad_sig, pending_id)

    # The committed candidate survived the rejected confirmation.
    assert _pending_addresses(session) == [b"alice"]

    # ... and is still finalizable with a valid signature.
    good_sig = sign_ward_update(c_counter, mac_for_sig, ward_id)
    counter, new_root, _wid, _mac = ward.confirmed_by_wm(
        session, c_counter, mac_t, good_sig, pending_id
    )
    _apply_device_leaf(tree, res)
    assert counter == new_counter
    assert new_root == tree.get_root_hash()
    assert _pending_addresses(session) == []


@pytest.mark.models("core")
def test_ward_discard_pending_clears_queue_and_unblocks(session: Session) -> None:
    """Explicit discard abandons a specific queued candidate (by pending_id) the
    host cannot finalize. It reports the discarded address and does NOT advance
    the device counter."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    pid_alice = _queue_update(
        session, b"alice", ENTRIES[b"alice"], b"data_alice_v2"
    )
    assert _pending_addresses(session) == [b"alice"]

    # Discard the stuck candidate by its pending_id.
    discarded_address, wallet_id = ward.discard_pending(session, pid_alice)
    assert discarded_address == b"alice"
    assert wallet_id is not None
    assert _pending_addresses(session) == []

    # The counter did not move (discard is not a finalize): the authenticated
    # state is still the pre-edit tree.
    valid, membership, dev_counter, _wid = _lookup_membership(session, tree, b"alice")
    assert valid and membership
    assert dev_counter == counter0

    # The queue is unblocked: a different edit can now be queued and finalized.
    pid_bob = _queue_update(session, b"bob", ENTRIES[b"bob"], b"data_bob_v2")
    assert _pending_addresses(session) == [b"bob"]
    counter, new_root, _wid, _mac = _perform_and_finalize(session, tree, pid_bob)
    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_discard_pending_idempotent_when_empty(session: Session) -> None:
    """Discarding with nothing queued for this wallet succeeds as a no-op and
    reports no discarded address."""
    tree = _make_tree()
    _seed_device(session, tree)

    assert _pending_addresses(session) == []
    discarded_address, wallet_id = ward.discard_pending(session)
    assert discarded_address is None
    assert wallet_id is not None
    assert _pending_addresses(session) == []
