"""Initial WARD synchronization driven by a fully emulated WARD Manager (WM).

Because device tests use the known "all all all ..." mnemonic, `ward_mgr_emu.WMEmulator`
can reproduce the device-keyed root_mac and mint valid attestations for a tree the
device has never written. That lets us exercise the sync round end-to-end,
including the negative cases that protect it (tampered mac, counter rollback,
replayed attestation)."""

import pytest

from trezorlib import exceptions, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session

from ...ward_mgr_emu import WMEmulator, wm_initial_sync

pytestmark = [pytest.mark.models("core")]

_ADDRESS = "bc1qdemoaddress000000000000000000000000000"
_OTHER = "bc1qotheraddress000000000000000000000000000"
_VALUE = b'TEST:1:{"label":"label1"}'
_OTHER_VALUE = b'TEST:1:{"label":"label2"}'


def _foreign_tree() -> WARDTree:
    """A tree the device has never seen, with leaves stamped as a real history
    would leave them (counters 1 and 2 => global counter 2)."""
    tree = WARDTree()
    tree.insert(_ADDRESS.encode(), _VALUE, counter=1)
    tree.insert(_OTHER.encode(), _OTHER_VALUE, counter=2)
    return tree


def test_ward_initial_sync_adopts_foreign_tree(session: Session) -> None:
    """The WM attests a pre-populated tree; the device adopts it as its
    authenticated root even though it never computed it."""
    wm = WMEmulator()
    tree = _foreign_tree()

    counter, adopted_root, root_mac = wm_initial_sync(session, wm, tree, counter=2)

    assert counter == 2
    assert adopted_root == tree.get_root_hash()
    assert root_mac is not None

    # The adopted root is genuinely authenticated: membership proofs verify
    # on-device against it, at the leaf counters the WM committed.
    valid, membership, current, _wallet_id = ward.lookup(
        session,
        _ADDRESS.encode(),
        _VALUE,
        tree.get_proof(_ADDRESS.encode()),
        counter=1,
    )
    assert valid and membership
    assert current == 2

    valid, membership, _current, _wallet_id = ward.lookup(
        session,
        _OTHER.encode(),
        _OTHER_VALUE,
        tree.get_proof(_OTHER.encode()),
        counter=2,
    )
    assert valid and membership


def test_ward_initial_sync_rejects_incorrect_wm_signature(session: Session) -> None:
    """Same setup as test_ward_initial_sync_adopts_foreign_tree, but the freshness
    attestation is signed by an untrusted key (not the WM). The device rejects it
    at ingest and adopts nothing."""
    wm = WMEmulator()
    # An impostor "WM" whose Ed25519 key the device does not trust.
    impostor = WMEmulator(qm_seed=b"NOT THE WARD MANAGER DEBUG KEY!!")
    tree = _foreign_tree()
    root = tree.get_root_hash()

    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None

    # The mac is correct; only the signature is bad, so the failure is unambiguous.
    mac = wm.root_mac(wallet_id, 2, root)
    nonce = ward.sync(session)
    bad_sig = impostor.sign_attestation(wallet_id, nonce, 2, mac)

    with pytest.raises(
        exceptions.TrezorFailure, match="attestation verification failed"
    ):
        ward.ingest_attestation(session, 2, mac, bad_sig)

    # Nothing was adopted: there is no authenticated root in the session.
    with pytest.raises(
        exceptions.TrezorFailure, match="no authenticated root in session"
    ):
        ward.lookup(
            session,
            _ADDRESS.encode(),
            _VALUE,
            tree.get_proof(_ADDRESS.encode()),
            counter=1,
        )


def test_ward_initial_sync_empty_tree(session: Session) -> None:
    """Fresh-wallet bootstrap: attest the empty tree (counter 0, ZERO_MAC)."""
    wm = WMEmulator()

    counter, adopted_root, _root_mac = wm_initial_sync(
        session, wm, WARDTree(), counter=0
    )

    assert counter == 0
    assert adopted_root is None


def test_ward_sync_refresh_moves_counter_forward(session: Session) -> None:
    """After adopting one state, a later attestation at a higher counter moves the
    device forward to the newer tree (refresh, not just initial bootstrap)."""
    wm = WMEmulator()

    tree1 = WARDTree()
    tree1.insert(_ADDRESS.encode(), _VALUE, counter=1)
    counter, root1, _mac = wm_initial_sync(session, wm, tree1, counter=1)
    assert counter == 1
    assert root1 == tree1.get_root_hash()

    tree2 = _foreign_tree()  # {_ADDRESS@1, _OTHER@2}
    counter, root2, _mac = wm_initial_sync(session, wm, tree2, counter=2)
    assert counter == 2
    assert root2 == tree2.get_root_hash()

    # The refreshed root authenticates the newly-added entry at the new counter.
    valid, membership, current, _wallet_id = ward.lookup(
        session,
        _OTHER.encode(),
        _OTHER_VALUE,
        tree2.get_proof(_OTHER.encode()),
        counter=2,
    )
    assert valid and membership
    assert current == 2


def test_ward_sync_idempotent_at_same_counter(session: Session) -> None:
    """Re-attesting the current state at the current counter (counter ==
    counter_loc) is accepted; adopt is idempotent."""
    wm = WMEmulator()
    tree = _foreign_tree()

    counter, root, _mac = wm_initial_sync(session, wm, tree, counter=2)
    assert counter == 2

    counter2, root2, _mac2 = wm_initial_sync(session, wm, tree, counter=2)
    assert counter2 == 2
    assert root2 == root


def test_ward_sync_rejects_wrong_root_mac(session: Session) -> None:
    """reconcile binds the host-supplied root to the attested mac via the device's
    own key; a mac the device can't reproduce is rejected."""
    wm = WMEmulator()
    tree = _foreign_tree()
    root = tree.get_root_hash()
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None

    good_mac = wm.root_mac(wallet_id, 2, root)
    bad_mac = bytes([good_mac[0] ^ 0xFF]) + good_mac[1:]

    # Sign the tampered mac so it clears the attestation signature check; it must
    # then fail the root<->mac binding in reconcile.
    nonce = ward.sync(session)
    sig = wm.sign_attestation(wallet_id, nonce, 2, bad_mac)
    ward.ingest_attestation(session, 2, bad_mac, sig)

    with pytest.raises(
        exceptions.TrezorFailure, match="root does not match the attested mac"
    ):
        ward.reconcile(session, root)


def test_ward_sync_rejects_counter_mac_mismatch(session: Session) -> None:
    """The counter is bound BOTH into the WM signature and into the root_mac.
    reconcile recomputes the mac using the *signed* counter, so an attestation
    whose signed counter differs from the counter its mac was computed for is
    rejected -- even though the signature is internally self-consistent. This
    prevents pairing a valid freshness signature for counter N with a mac that
    authorizes a different counter's state."""
    wm = WMEmulator()
    tree = _foreign_tree()
    root = tree.get_root_hash()
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None

    signed_counter = 2
    # A mac computed for a DIFFERENT counter than the one the WM will sign.
    mismatched_mac = wm.root_mac(wallet_id, signed_counter + 1, root)

    # Sign (signed_counter, mismatched_mac) consistently, so ingest's signature and
    # counter checks both pass; the mismatch must surface at reconcile.
    nonce = ward.sync(session)
    sig = wm.sign_attestation(wallet_id, nonce, signed_counter, mismatched_mac)
    ward.ingest_attestation(session, signed_counter, mismatched_mac, sig)

    with pytest.raises(
        exceptions.TrezorFailure, match="root does not match the attested mac"
    ):
        ward.reconcile(session, root)


def test_ward_sync_rejects_counter_rollback(session: Session) -> None:
    """After adopting counter 2, an attestation carrying an older counter is
    rejected (anti-rollback)."""
    wm = WMEmulator()
    tree = _foreign_tree()

    counter, root, _mac = wm_initial_sync(session, wm, tree, counter=2)
    assert counter == 2

    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    stale_counter = 1
    mac = wm.root_mac(wallet_id, stale_counter, root)
    nonce = ward.sync(session)
    sig = wm.sign_attestation(wallet_id, nonce, stale_counter, mac)

    with pytest.raises(
        exceptions.TrezorFailure, match="older than counter_loc"
    ):
        ward.ingest_attestation(session, stale_counter, mac, sig)


def test_ward_sync_rejects_rollback_after_progress(session: Session) -> None:
    """Monotonicity holds across refreshes: after moving 1 -> 2, an attestation
    carrying the older counter 1 is rejected."""
    wm = WMEmulator()

    tree1 = WARDTree()
    tree1.insert(_ADDRESS.encode(), _VALUE, counter=1)
    wm_initial_sync(session, wm, tree1, counter=1)
    _counter, root2, _mac = wm_initial_sync(session, wm, _foreign_tree(), counter=2)
    assert root2 is not None

    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    mac = wm.root_mac(wallet_id, 1, tree1.get_root_hash())
    nonce = ward.sync(session)
    sig = wm.sign_attestation(wallet_id, nonce, 1, mac)

    with pytest.raises(
        exceptions.TrezorFailure, match="older than counter_loc"
    ):
        ward.ingest_attestation(session, 1, mac, sig)


def test_ward_sync_rejects_replayed_attestation(session: Session) -> None:
    """An attestation minted for one sync round cannot be replayed after a new
    WARDSync mints a fresh nonce."""
    wm = WMEmulator()
    tree = _foreign_tree()
    root = tree.get_root_hash()
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    mac = wm.root_mac(wallet_id, 2, root)

    nonce1 = ward.sync(session)
    sig = wm.sign_attestation(wallet_id, nonce1, 2, mac)  # valid for round 1

    ward.sync(session)  # a new round supersedes nonce1

    with pytest.raises(
        exceptions.TrezorFailure, match="attestation verification failed"
    ):
        ward.ingest_attestation(session, 2, mac, sig)  # replay round-1 attestation
