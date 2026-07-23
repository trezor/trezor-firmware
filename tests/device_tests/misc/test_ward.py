"""Device tests for the WARD write round (set_entry -> commit -> finalize),
the decomposition of the former fused AuthDbUpdateLeaf.

Each write is driven either through the individual wrappers (to observe the
intermediate state) or through the ward.write() convenience. The WARD Manager's
final attestation is signed locally with the debug WM key (ward.DEBUG_QM_SEED),
accepted only on debug firmware.
"""

import pytest

from trezorlib import btc, ward
from trezorlib.authdb_tree import AuthDbTree
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

ENTRIES = {
    b"alice": b"data_alice",
    b"bob": b"data_bob",
    b"carol": b"data_carol",
    b"dave": b"data_dave",
}


def _make_tree() -> AuthDbTree:
    tree = AuthDbTree()
    for addr, val in ENTRIES.items():
        tree.insert(addr, val, counter=1)
    return tree


def _seed_device(session: Session, tree: AuthDbTree) -> int:
    """Install the host tree's root on the device (debug injection) and return the
    device counter it now sits at."""
    counter, _root, _wid, _mac = ward.debug_set_root(session, tree.get_root_hash())
    return counter


@pytest.mark.models("core")
def test_ward_update(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    counter, new_root, wallet_id, root_mac = ward.write(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"data_alice_v2",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )

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
    counter, new_root, _wid, _mac = ward.write(
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

    tree.insert(b"erin", b"data_erin", counter=new_counter)
    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_delete(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)

    new_counter = counter0 + 1
    counter, new_root, _wid, _mac = ward.write(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )

    tree.delete(b"alice")
    assert counter == new_counter
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_ward_counter_advances_only_at_finalize(session: Session) -> None:
    """set_entry + commit must NOT advance the device counter; only finalize does."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    ward.set_entry(
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

    sig = ward.sign_ward_final(c_counter, mac_t, wallet_id)
    counter, _new_root, _wid, _root_mac = ward.finalize(session, c_counter, mac_t, sig)
    assert counter == new_counter  # advanced now


@pytest.mark.models("core")
def test_ward_finalize_bad_signature_rejected(session: Session) -> None:
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    ward.set_entry(
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
        ward.finalize(session, c_counter, mac_t, bad_sig)


@pytest.mark.models("core")
def test_ward_second_set_entry_rejected_while_pending(session: Session) -> None:
    """Offline queue depth 1: a second SetEntry while one is pending is rejected."""
    tree = _make_tree()
    counter0 = _seed_device(session, tree)
    new_counter = counter0 + 1

    ward.set_entry(
        session,
        address=b"alice",
        old_value=ENTRIES[b"alice"],
        new_value=b"data_alice_v2",
        new_counter=new_counter,
        proof=tree.get_proof(b"alice"),
        old_counter=tree.get_counter(b"alice"),
    )
    with pytest.raises(TrezorFailure):
        ward.set_entry(
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
    out_counter, new_root, _wid, _rm = ward.bootstrap(
        session, counter, mac, root
    )
    assert out_counter == counter
    assert new_root == root


@pytest.mark.models("core")
def test_ward_ingest_bad_signature_rejected(session: Session) -> None:
    tree = _make_tree()
    counter, _r, _wid, mac = ward.debug_set_root(session, tree.get_root_hash())

    ward.init_sync(session)
    with pytest.raises(TrezorFailure):
        ward.ingest_attestation(session, counter, mac, bytes(64))  # invalid wm_sig


@pytest.mark.models("core")
def test_ward_ingest_rollback_rejected(session: Session) -> None:
    """An attested counter below the device floor is rejected (anti-rollback)."""
    tree = _make_tree()
    # advance the device to counter 2
    ward.debug_set_root(session, tree.get_root_hash())
    counter, _r, wallet_id, mac = ward.debug_set_root(session, tree.get_root_hash())
    assert counter >= 2

    # Attest a stale counter 1 < counter_loc with a correctly-signed attestation.
    nonce, _v, _wid = ward.init_sync(session)
    sig = ward.sign_wm_attestation(nonce, 1, mac, wallet_id)
    with pytest.raises(TrezorFailure):
        ward.ingest_attestation(session, 1, mac, sig)


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
    tree = AuthDbTree()
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
