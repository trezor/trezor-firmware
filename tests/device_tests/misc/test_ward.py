"""Device tests for the WARD write round (add_pending -> commit -> finalize),
the decomposition of the former fused AuthDbUpdateLeaf.

Each write is driven either through the individual wrappers (to observe the
intermediate state or through an equivalent host-side helper sequence. The WARD
Manager's final attestation is signed locally with the debug WM key
(ward.DEBUG_QM_SEED), accepted only on debug firmware.
"""

import pytest

from trezorlib import btc, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

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
    def sign_attestation(wallet_id: bytes, nonce: bytes, counter: int, mac: bytes) -> bytes:
        return ward.sign_wm_attestation(nonce, counter, mac, wallet_id)

    @staticmethod
    def sign_final(wallet_id: bytes, counter: int, mac: bytes) -> bytes:
        return ward.sign_ward_update(counter, mac, wallet_id)


class WardHostHarness:
    """In-memory host harness for WARD end-to-end tests.

    Keeps the authenticated Merkle state in WARDTree and the attested
    (root, counter, root_mac) blob in the Evolu-like store.
    """

    def __init__(self) -> None:
        self.tree = WARDTree()
        self.store = InMemoryEvoluStore()
        self.wm = InMemoryWardManager()
        self.queue: list[tuple[bytes, bytes]] = []

    def bootstrap_device(self, session: Session) -> tuple[int, bytes | None, bytes | None, bytes | None]:
        root, counter, root_mac = self.store.get_root()
        nonce = ward.sync(session)
        _pending, wallet_id = ward.list_pending(session)
        assert wallet_id is not None
        mac_for_sig = root_mac if root_mac is not None else ward.ZERO_MAC
        sig = self.wm.sign_attestation(wallet_id, nonce, counter, mac_for_sig)
        ward.ingest_attestation(session, counter, root_mac, sig)
        out_counter, out_root, out_root_mac = ward.reconcile(session, root)
        return out_counter, out_root, wallet_id, out_root_mac

    def lookup(self, session: Session, address: bytes) -> bytes | None:
        if self.tree.get_counter(address):
            value = self.tree.get_value(address)
            valid, membership, _counter, _wallet_id = ward.lookup(
                session,
                address=address,
                value=value,
                proof=self.tree.get_proof(address),
                counter=self.tree.get_counter(address),
            )
            assert valid and membership
            return value

        proof, witness_address, witness_counter, witness_value = (
            self.tree.get_nonmembership_proof(address)
        )
        valid, membership, _counter, _wallet_id = ward.lookup(
            session,
            address=address,
            value=None,
            proof=proof,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
        )
        assert valid and not membership
        return None

    def set_value(self, session: Session, address: bytes, value: bytes | None) -> int:
        self.bootstrap_device(session)

        new_counter = self.store.counter + 1
        old_counter = self.tree.get_counter(address)
        if old_counter:
            old_value = self.tree.get_value(address)
            proof = self.tree.get_proof(address)
            witness_address = witness_value = None
            witness_counter = None
        else:
            old_value = b""
            proof, witness_address, witness_counter, witness_value = (
                self.tree.get_nonmembership_proof(address)
            )

        ward.add_pending(
            session,
            address=address,
            old_value=old_value,
            new_value=value or b"",
            new_counter=new_counter,
            proof=proof,
            old_counter=old_counter or None,
            witness_address=witness_address,
            witness_value=witness_value,
            witness_counter=witness_counter,
        )
        c_counter, _root_t, mac_t, wallet_id = ward.commit(session)
        mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
        assert wallet_id is not None
        sig = self.wm.sign_final(wallet_id, c_counter, mac_for_sig)
        counter, new_root, _wallet_id, root_mac = ward.confirm_commit(
            session, c_counter, mac_t, sig
        )

        if value is None:
            self.tree.delete(address)
        else:
            self.tree.insert(address, value, counter=new_counter)

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
    tree = WARDTree()
    for addr, val in ENTRIES.items():
        tree.insert(addr, val, counter=1)
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
    nonce = ward.sync(session)
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    mac_for_sig = root_mac if root_mac is not None else ward.ZERO_MAC
    sig = ward.sign_wm_attestation(nonce, counter, mac_for_sig, wallet_id)
    ward.ingest_attestation(session, counter, root_mac, sig)
    out_counter, out_root, out_root_mac = ward.reconcile(session, root)
    return out_counter, out_root, wallet_id, out_root_mac


def _finalize_pending(
    session: Session,
) -> tuple[int, bytes | None, bytes | None, bytes | None]:
    c_counter, _root_t, mac_t, wallet_id = ward.commit(session)
    mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
    assert wallet_id is not None
    sig = ward.sign_ward_update(c_counter, mac_for_sig, wallet_id)
    return ward.confirm_commit(session, c_counter, mac_t, sig)


@pytest.mark.models("core")
def test_ward_update(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    ward.add_pending(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"data_alice_v2",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )
    counter, new_root, wallet_id, root_mac = _finalize_pending(session)

    tree.insert(b"alice", b"data_alice_v2", counter=new_counter)
    assert counter == new_counter
    assert new_root == tree.get_root_hash()
    assert root_mac is not None
    assert wallet_id is not None and len(wallet_id) == 20


@pytest.mark.models("core")
def test_ward_insert(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    proof, w_addr, w_counter, w_value = tree.get_nonmembership_proof(b"erin")
    ward.add_pending(
        session,
        address=b"erin",
        old_value=b"",
        new_value=b"data_erin",
        new_counter=new_counter,
        proof=proof,
        witness_address=w_addr,
        witness_counter=w_counter,
        witness_value=w_value,
    )
    counter, new_root, _wid, _mac = _finalize_pending(session)

    tree.insert(b"erin", b"data_erin", counter=new_counter)
    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_delete(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    ward.add_pending(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )
    counter, new_root, _wid, _mac = _finalize_pending(session)

    tree.delete(b"alice")
    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_counter_advances_only_at_finalize(session: Session) -> None:
    """add_pending + commit must NOT advance the device counter; only finalize does."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    ward.add_pending(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"data_alice_v2",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )
    c_counter, root_t, mac_t, wallet_id = ward.commit(session)

    # After commit, the authenticated root/counter are still the pre-edit ones.
    valid, membership, dev_counter, _wid = ward.lookup(
        session,
        address=b"alice",
        value=ENTRIES[b"alice"],
        counter=tree.get_counter(b"alice"),
        proof=tree.get_proof(b"alice"),
    )
    assert valid and membership
    assert dev_counter == counter0  # not advanced yet

    sig = ward.sign_ward_update(c_counter, mac_t, wallet_id)
    counter, _new_root, _wid, _root_mac = ward.confirm_commit(session, c_counter, mac_t, sig)
    assert counter == new_counter  # advanced now


@pytest.mark.models("core")
def test_ward_finalize_bad_signature_rejected(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    ward.add_pending(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"data_alice_v2",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )
    c_counter, _root_t, mac_t, _wallet_id = ward.commit(session)

    bad_sig = bytes(64)  # not a valid WM signature
    with pytest.raises(TrezorFailure):
        ward.confirm_commit(session, c_counter, mac_t, bad_sig)


@pytest.mark.models("core")
def test_ward_second_set_entry_rejected_while_pending(session: Session) -> None:
    """Offline queue depth 1: a second add_pending while one is pending is rejected."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    ward.add_pending(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"data_alice_v2",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )
    with pytest.raises(TrezorFailure):
        ward.add_pending(
            session,
            address=b"bob",
            old_value=ENTRIES[b"bob"],
            new_value=b"data_bob_v2",
            new_counter=new_counter,
            proof=tree.get_proof(b"bob"),
            old_counter=tree.get_counter(b"bob"),
        )


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

    nonce = ward.sync(session)
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    valid_sig = ward.sign_wm_attestation(nonce, counter, mac, wallet_id)
    bad_sig = bytes([valid_sig[0] ^ 0x01]) + valid_sig[1:]
    with pytest.raises(TrezorFailure):
        ward.ingest_attestation(session, counter, mac, bad_sig)


@pytest.mark.models("core")
def test_ward_ingest_rollback_rejected(session: Session) -> None:
    """An attested counter below the device floor is rejected (anti-rollback)."""
    tree = _make_tree()
    # advance the device to counter 2
    ward.debug_set_root(session, tree.get_root_hash())
    counter, _r, wallet_id, mac = ward.debug_set_root(session, tree.get_root_hash())
    assert counter >= 2

    # Attest a stale counter 1 < counter_loc with a correctly-signed attestation.
    nonce = ward.sync(session)
    sig = ward.sign_wm_attestation(nonce, 1, mac, wallet_id)
    with pytest.raises(TrezorFailure):
        ward.ingest_attestation(session, 1, mac, sig)


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
    tree.insert(address.encode(), b"alice.btc", counter=1)

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
        ward_proof=tree.get_proof(address.encode()),
        ward_counter=1,
    )
    assert result.address == address
