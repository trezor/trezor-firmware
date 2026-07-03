from hashlib import sha256

import pytest

from trezorlib import authdb
from trezorlib.authdb_tree import AuthDbTree, EMPTY_ROOT
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

ENTRIES = {
    b"alice": b"data_alice",
    b"bob":   b"data_bob",
    b"carol": b"data_carol",
    b"dave":  b"data_dave",
}


def _make_tree() -> AuthDbTree:
    tree = AuthDbTree()
    for addr, val in ENTRIES.items():
        tree.insert(addr, val)
    return tree


@pytest.mark.models("core")
def test_set_root_returns_incremented_counter(session: Session) -> None:
    tree = _make_tree()
    counter1, identifier1 = authdb.set_root(session, tree.get_root_hash())
    counter2, identifier2 = authdb.set_root(session, tree.get_root_hash())
    assert counter2 == counter1 + 1
    assert identifier1 == identifier2  # same seed → same identifier


@pytest.mark.models("core")
def test_identifier_is_32_bytes(session: Session) -> None:
    tree = _make_tree()
    _counter, identifier = authdb.set_root(session, tree.get_root_hash())
    assert identifier is not None
    assert len(identifier) == 32


@pytest.mark.models("core")
def test_identifier_consistent_across_calls(session: Session) -> None:
    """Same seed/passphrase must produce the same identifier on every call."""
    tree = _make_tree()
    _, id1 = authdb.set_root(session, tree.get_root_hash())
    _, id2 = authdb.set_root(session, tree.get_root_hash())
    proof = tree.get_proof(b"alice")
    _, _, _, id3 = authdb.lookup(session, address=b"alice", value=b"data_alice", proof=proof)
    assert id1 == id2 == id3


@pytest.mark.models("core")
@pytest.mark.parametrize("address,value", list(ENTRIES.items()))
def test_lookup_valid_proof(session: Session, address: bytes, value: bytes) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(address)
    valid, membership, counter, identifier = authdb.lookup(
        session, address=address, value=value, proof=proof
    )

    assert valid is True
    assert membership is True
    assert counter > 0
    assert identifier is not None and len(identifier) == 32


@pytest.mark.models("core")
def test_lookup_invalid_wrong_value(session: Session) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(b"alice")
    valid, _membership, _counter, _identifier = authdb.lookup(
        session, address=b"alice", value=b"WRONG", proof=proof
    )
    assert valid is False


@pytest.mark.models("core")
def test_lookup_invalid_wrong_address(session: Session) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    # alice's proof, but claim address=bob — path mismatch
    proof = tree.get_proof(b"alice")
    valid, _membership, _counter, _identifier = authdb.lookup(
        session, address=b"bob", value=b"data_alice", proof=proof
    )
    assert valid is False


@pytest.mark.models("core")
def test_lookup_invalid_wrong_root(session: Session) -> None:
    from hashlib import sha256

    wrong_root = sha256(b"wrong").digest()
    authdb.set_root(session, wrong_root)

    tree = _make_tree()
    proof = tree.get_proof(b"alice")
    valid, _membership, _counter, _identifier = authdb.lookup(
        session, address=b"alice", value=b"data_alice", proof=proof
    )
    assert valid is False


@pytest.mark.models("core")
def test_lookup_no_root_membership_returns_false(session: Session) -> None:
    """Membership query against empty tree returns valid=False, membership=True."""
    tree = _make_tree()
    proof = tree.get_proof(b"alice")
    valid, membership, counter, identifier = authdb.lookup(
        session, address=b"alice", value=b"data_alice", proof=proof
    )
    assert valid is False
    assert membership is True
    assert identifier is not None and len(identifier) == 32


@pytest.mark.models("core")
def test_lookup_no_root_nonmembership_returns_true(session: Session) -> None:
    """Non-membership query against empty tree returns valid=True, membership=False."""
    valid, membership, counter, identifier = authdb.lookup(
        session,
        address=b"alice",
        value=None,
        proof=[],
        witness_address=None,
        witness_value=None,
    )
    assert valid is True
    assert membership is False
    assert identifier is not None and len(identifier) == 32


@pytest.mark.models("core")
def test_verify_proof_host_matches_device(session: Session) -> None:
    """Confirm host-side AuthDbTree.verify_proof produces the same result as device."""
    tree = _make_tree()
    root = tree.get_root_hash()
    authdb.set_root(session, root)

    for address, value in ENTRIES.items():
        proof = tree.get_proof(address)
        host_result = AuthDbTree.verify_proof(address, value, proof, root)
        device_valid, _, _, _ = authdb.lookup(
            session, address=address, value=value, proof=proof
        )
        assert host_result == device_valid is True


# ---------------------------------------------------------------------------
# Non-membership proofs
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
def test_nonmembership_proof_valid(session: Session) -> None:
    """Non-member address returns valid=True, membership=False."""
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    target = b"zara"
    proof, w_addr, w_val = tree.get_nonmembership_proof(target)
    assert w_addr is not None

    valid, membership, counter, identifier = authdb.lookup(
        session,
        address=target,
        value=None,
        proof=proof,
        witness_address=w_addr,
        witness_value=w_val,
    )
    assert valid is True
    assert membership is False
    assert counter > 0
    assert identifier is not None and len(identifier) == 32


@pytest.mark.models("core")
def test_nonmembership_proof_member_returns_false(session: Session) -> None:
    """Non-membership proof for a member should fail because witness == target."""
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    # Use a real member as the "non-member target"; the witness found will
    # be the leaf itself, which makes witness_address == address → invalid.
    proof = tree.get_proof(b"alice")
    valid, _membership, _counter, _identifier = authdb.lookup(
        session,
        address=b"alice",
        value=None,
        proof=proof,
        witness_address=b"alice",
        witness_value=b"data_alice",
    )
    assert valid is False


@pytest.mark.models("core")
def test_nonmembership_host_matches_device(session: Session) -> None:
    """Host-side verify_nonmembership matches device."""
    tree = _make_tree()
    root = tree.get_root_hash()
    authdb.set_root(session, root)

    target = b"zara"
    proof, w_addr, w_val = tree.get_nonmembership_proof(target)

    host = AuthDbTree.verify_nonmembership(target, proof, w_addr, w_val, root)
    device_valid, device_membership, _, _ = authdb.lookup(
        session,
        address=target,
        value=None,
        proof=proof,
        witness_address=w_addr,
        witness_value=w_val,
    )
    assert host is True
    assert device_valid is True
    assert device_membership is False


# ---------------------------------------------------------------------------
# update_leaf
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
def test_update_leaf_init(session: Session) -> None:
    """INIT: insert first entry into an empty tree."""
    counter, new_root, identifier, new_mac, auth_mac = authdb.update_leaf(
        session,
        address=b"alice",
        old_value=b"",
        new_value=b"data_alice",
        proof=[],
    )
    assert new_root is not None
    assert counter > 0
    assert identifier is not None and len(identifier) == 32
    assert new_mac is not None and len(new_mac) == 32
    assert auth_mac is not None and len(auth_mac) == 32  # debug mode returns auth_mac
    # Host-side tree should match
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_update_leaf_insert(session: Session) -> None:
    """INSERT: add a second entry to an existing tree."""
    # Bootstrap with alice
    counter0, root0, _, _mac0, _auth_mac0 = authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )

    # Build host tree with alice to get non-membership proof for bob
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    assert tree.get_root_hash() == root0

    proof, w_addr, w_val = tree.get_nonmembership_proof(b"bob")
    counter1, new_root, identifier, _mac1, _auth_mac1 = authdb.update_leaf(
        session,
        address=b"bob",
        old_value=b"",
        new_value=b"data_bob",
        proof=proof,
        witness_address=w_addr,
        witness_value=w_val,
    )
    assert counter1 == counter0 + 1
    tree.insert(b"bob", b"data_bob")
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_update_leaf_update(session: Session) -> None:
    """UPDATE: change the value of an existing entry."""
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(b"alice")
    counter, new_root, identifier, _mac, _auth_mac = authdb.update_leaf(
        session,
        address=b"alice",
        old_value=b"data_alice",
        new_value=b"data_alice_v2",
        proof=proof,
    )
    tree.insert(b"alice", b"data_alice_v2")
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_update_leaf_delete(session: Session) -> None:
    """DELETE: remove an entry; single-entry tree becomes empty."""
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(b"alice")
    counter, new_root, identifier, del_mac, _del_auth_mac = authdb.update_leaf(
        session,
        address=b"alice",
        old_value=b"data_alice",
        new_value=b"",
        proof=proof,
    )
    assert new_root is None  # tree is empty
    assert del_mac is None   # no root → no MAC


@pytest.mark.models("core")
def test_update_leaf_delete_to_empty_returns_incremented_counter(session: Session) -> None:
    """Regression guard: deleting the only remaining leaf must still bump the
    counter and succeed, not raise "No record for identifier". Built via
    update_leaf() INIT (not set_root()) so this exercises only the
    clear_root()/increment_counter() ordering fix in update_leaf.py, without
    depending on AuthDbSetRoot's separate mac/device_id requirements."""
    counter0, _root0, identifier, _mac0, _auth_mac0 = authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )

    counter1, new_root, identifier2, del_mac, _auth_mac1 = authdb.update_leaf(
        session,
        address=b"alice",
        old_value=b"data_alice",
        new_value=b"",
        proof=[],
    )
    assert new_root is None  # tree is empty
    assert del_mac is None   # no root -> no MAC
    assert counter1 == counter0 + 1
    assert identifier2 == identifier

    # The identity must be fully usable afterwards (record wasn't left in a
    # half-deleted state): a fresh INIT should work exactly as before. Note
    # clear_root() deletes the whole identity record, so the counter starts
    # over from 0 here rather than continuing from counter1 -- a separate,
    # pre-existing quirk of that design, not something this fix changes.
    counter2, root2, _identifier3, _mac2, _auth_mac2 = authdb.update_leaf(
        session, address=b"bob", old_value=b"", new_value=b"data_bob", proof=[]
    )
    assert root2 is not None
    assert counter2 == 1


@pytest.mark.models("core")
def test_update_leaf_wrong_old_value_rejected(session: Session) -> None:
    """UPDATE with wrong old_value must be rejected."""
    from trezorlib.exceptions import TrezorFailure

    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(b"alice")
    with pytest.raises(TrezorFailure):
        authdb.update_leaf(
            session,
            address=b"alice",
            old_value=b"WRONG",
            new_value=b"data_alice_v2",
            proof=proof,
        )


# ---------------------------------------------------------------------------
# approve() + update_leaf(mac=...) pre-authorization flow
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
@pytest.mark.xfail(
    strict=True,
    reason=(
        "approve() computes mac=HMAC(mac_key, address||value) but update_leaf() "
        "verifies HMAC(mac_key, old_leaf_hash||new_leaf_hash) -- different "
        "preimages, so an approve()-issued MAC never validates in update_leaf(). "
        "See core/src/apps/authdb/approve.py vs update_leaf.py."
    ),
)
def test_approve_then_update_leaf_with_mac(session: Session) -> None:
    """A MAC obtained via AuthDbApprove should let update_leaf skip confirmation."""
    from trezorlib import messages

    address, value = b"alice", b"data_alice"
    approve_resp = session.call(
        messages.AuthDbApprove(address=address, value=value),
        expect=messages.AuthDbApproveResponse,
    )

    counter, new_root, identifier, _mac, _auth_mac = authdb.update_leaf(
        session,
        address=address,
        old_value=b"",
        new_value=value,
        proof=[],
        mac=approve_resp.mac,
        device_id=approve_resp.identifier,
    )
    assert new_root is not None
    assert identifier == approve_resp.identifier


# ---------------------------------------------------------------------------
# AuthDbSetDeviceId -- emulate multiple devices/identities on one emulator
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
def test_set_device_id_switches_identity(session: Session) -> None:
    """Switching device_id (debug-only) must fully isolate the Merkle root."""
    id_a = sha256(b"identity-a").digest()
    id_b = sha256(b"identity-b").digest()

    authdb.set_device_id(session, id_a)
    counter_a, root_a, ident_a, _mac, _auth_mac = authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )
    assert ident_a == id_a
    assert root_a is not None

    authdb.set_device_id(session, id_b)
    # Fresh identity: lookup for the address written under id_a must show
    # an empty tree, i.e. no cross-identity root leakage.
    valid, membership, _counter, ident_b = authdb.lookup(
        session, address=b"alice", value=b"data_alice", proof=[]
    )
    assert ident_b == id_b
    assert membership is True
    assert valid is False  # empty tree under id_b -> membership query is false

    # Switching back to id_a must see the original root untouched.
    authdb.set_device_id(session, id_a)
    valid_a, _membership_a, counter_a2, ident_a2 = authdb.lookup(
        session, address=b"alice", value=b"data_alice", proof=[]
    )
    assert ident_a2 == id_a
    assert valid_a is True
    assert counter_a2 == counter_a


@pytest.mark.models("core")
def test_multi_identity_root_confusion(session: Session) -> None:
    """A proof valid for identity A's tree must be rejected against identity B."""
    id_a = sha256(b"identity-a-confusion").digest()
    id_b = sha256(b"identity-b-confusion").digest()

    authdb.set_device_id(session, id_a)
    authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    proof = tree.get_proof(b"alice")

    authdb.set_device_id(session, id_b)
    # id_b's tree is empty; replaying an UPDATE proof that is valid for id_a
    # must be rejected, not silently accepted because it "looks" valid.
    with pytest.raises(TrezorFailure):
        authdb.update_leaf(
            session,
            address=b"alice",
            old_value=b"data_alice",
            new_value=b"data_alice_v2",
            proof=proof,
        )


# ---------------------------------------------------------------------------
# AuthDbSetRoot -- debug-only MAC/device_id enforcement
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
def test_set_root_wrong_device_id_rejected(session: Session) -> None:
    """device_id is checked before the MAC, so a mismatching device_id must
    fail even when the supplied MAC is garbage."""
    known_id = sha256(b"set-root-device-id").digest()
    wrong_id = sha256(b"not-the-current-identity").digest()
    authdb.set_device_id(session, known_id)

    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")

    with pytest.raises(TrezorFailure):
        authdb.set_root(
            session,
            tree.get_root_hash(),
            mac=b"\x00" * 32,
            device_id=wrong_id,
        )


@pytest.mark.models("core")
def test_set_root_forged_mac_rejected(session: Session) -> None:
    """Correct device_id but a forged MAC must still be rejected."""
    known_id = sha256(b"set-root-forged-mac").digest()
    authdb.set_device_id(session, known_id)

    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")

    with pytest.raises(TrezorFailure):
        authdb.set_root(
            session,
            tree.get_root_hash(),
            mac=b"\xff" * 32,  # cannot be a valid HMAC without the device key
            device_id=known_id,
        )


@pytest.mark.models("core")
def test_set_root_missing_mac_rejected(session: Session) -> None:
    """AuthDbSetRoot now requires mac+device_id unconditionally (see
    core/src/apps/authdb/set_root.py); calling it bare must fail, not
    silently inject the root. This guards against regressing back to the
    pre-MAC behaviour where an unauthenticated root could be injected."""
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")

    with pytest.raises(TrezorFailure):
        authdb.set_root(session, tree.get_root_hash())


# ---------------------------------------------------------------------------
# update_leaf MAC must be bound to the exact leaf transition, not just address
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
def test_update_leaf_mac_bound_to_wrong_value(session: Session) -> None:
    """An auth_mac issued for one new_value must not authorize a different one."""
    address = b"alice"

    _counter0, _root0, identifier, _mac0, auth_mac_for_v1 = authdb.update_leaf(
        session, address=address, old_value=b"", new_value=b"data_alice_v1", proof=[]
    )
    assert auth_mac_for_v1 is not None

    tree = AuthDbTree()
    tree.insert(address, b"data_alice_v1")
    proof = tree.get_proof(address)

    # Reuse the MAC issued for the v1 transition to authorize a v1->v2 update
    # with a *different* target value than what was actually approved.
    with pytest.raises(TrezorFailure):
        authdb.update_leaf(
            session,
            address=address,
            old_value=b"data_alice_v1",
            new_value=b"data_alice_v2_NOT_APPROVED",
            proof=proof,
            mac=auth_mac_for_v1,
            device_id=identifier,
        )


@pytest.mark.models("core")
def test_update_leaf_replayed_old_root_proof_rejected(session: Session) -> None:
    """A proof computed against a stale root must fail once the root moved on."""
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )
    stale_proof = tree.get_proof(b"alice")  # valid now, but not after the next line

    # Advance the tree with an unrelated insert -> root changes.
    nm_proof, w_addr, w_val = tree.get_nonmembership_proof(b"bob")
    authdb.update_leaf(
        session,
        address=b"bob",
        old_value=b"",
        new_value=b"data_bob",
        proof=nm_proof,
        witness_address=w_addr,
        witness_value=w_val,
    )

    # Replaying the now-stale proof for an update to alice must fail.
    with pytest.raises(TrezorFailure):
        authdb.update_leaf(
            session,
            address=b"alice",
            old_value=b"data_alice",
            new_value=b"data_alice_v2",
            proof=stale_proof,
        )


@pytest.mark.models("core")
def test_lookup_rejects_malformed_proof_element_length(session: Session) -> None:
    """Proof elements shorter than 33 bytes (bit + 32-byte sibling) must not
    crash the handler and must not be treated as valid."""
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    tree.insert(b"bob", b"data_bob")
    authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )
    nm_proof, w_addr, w_val = tree.get_nonmembership_proof(b"bob")
    authdb.update_leaf(
        session,
        address=b"bob",
        old_value=b"",
        new_value=b"data_bob",
        proof=nm_proof,
        witness_address=w_addr,
        witness_value=w_val,
    )

    real_proof = tree.get_proof(b"alice")
    truncated = [real_proof[0][:5]] if real_proof else [b"\x00" * 5]

    valid, _membership, _counter, _identifier = authdb.lookup(
        session, address=b"alice", value=b"data_alice", proof=truncated
    )
    assert valid is False


# ---------------------------------------------------------------------------
# Offline cache (AuthDbSetCacheEntry / GetCacheEntry / GetAllCache / WipeCache)
# ---------------------------------------------------------------------------

@pytest.mark.models("core")
def test_offline_cache_roundtrip(session: Session) -> None:
    address = b"cached-address"

    identifier_crc = authdb.set_cache_entry(session, address, label="My Label")
    assert isinstance(identifier_crc, int)

    found, label, data_mac = authdb.get_cache_entry(session, address)
    assert found is True
    assert label == "My Label"
    assert data_mac is None

    entries = authdb.get_all_cache(session)
    assert (address, "My Label", None) in entries

    # Absent fields clear on upsert: re-set with label=None clears the label.
    authdb.set_cache_entry(session, address, label=None)
    found2, label2, _data_mac2 = authdb.get_cache_entry(session, address)
    assert found2 is True
    assert label2 is None

    authdb.wipe_cache(session)
    found3, label3, data_mac3 = authdb.get_cache_entry(session, address)
    assert found3 is False
    assert label3 is None
    assert data_mac3 is None


@pytest.mark.models("core")
def test_cache_not_isolated_across_device_id_switch(session: Session) -> None:
    """Documents current behaviour: the offline cache has no identity scoping
    at all (core/src/storage/authdb.py stores it in one flat namespace, unlike
    the per-identifier `_ROOTS` table), so switching device_id does not
    segregate cache entries the way it does for Merkle roots. See
    TestAuthDbStorageIsolation.test_cache_not_isolated_per_identity in
    core/tests/test_apps.authdb.py for the storage-layer version of this."""
    id_a = sha256(b"cache-identity-a").digest()
    id_b = sha256(b"cache-identity-b").digest()
    address = b"shared-cache-address"

    authdb.set_device_id(session, id_a)
    authdb.set_cache_entry(session, address, label="label-for-a")

    authdb.set_device_id(session, id_b)
    found, label, _data_mac = authdb.get_cache_entry(session, address)
    # BUG: this entry was written under a different identity, yet it's
    # visible here. If cache isolation is added, flip this to found is False.
    assert found is True
    assert label == "label-for-a"


# ---------------------------------------------------------------------------
# Offline synchronization: AuthDbQueueOfflineOperation / GetOfflineOperations /
# AuthDbApplyOfflineOperations / AuthDbDeleteOfflineOperations
# ---------------------------------------------------------------------------

def _rebase(op: "authdb.OfflineOperation", proof, w_addr=None, w_val=None):
    """Build a RebasedOperation forwarding an OfflineOperation's signed fields
    byte-for-byte, the way a real rebase engine must (see review notes)."""
    return authdb.RebasedOperation(
        sequence=op.sequence,
        address=op.address,
        old_value=op.old_value,
        new_value=op.new_value,
        mac=op.mac,
        proof=proof,
        witness_address=w_addr,
        witness_value=w_val,
    )


@pytest.mark.models("core")
def test_offline_sync_full_lifecycle(session: Session) -> None:
    """End-to-end: queue while "offline", upload, rebase (simulated host-side
    with a local AuthDbTree), apply, then garbage collect."""
    seq1, mac1, identifier = authdb.queue_offline_operation(
        session, address=b"alice", old_value=b"", new_value=b"data_alice"
    )
    assert seq1 == 1

    current_root, counter0, _identifier, ops = authdb.get_offline_operations(session)
    assert current_root is None  # nothing applied yet
    assert len(ops) == 1
    assert ops[0].sequence == 1
    assert ops[0].mac == mac1

    tree = AuthDbTree()
    rebased1 = _rebase(ops[0], proof=[])  # INIT: empty tree, no proof needed
    tree.insert(b"alice", b"data_alice")

    applied_count, new_root, counter, last_applied, ident2 = authdb.apply_offline_operations(
        session, [rebased1]
    )
    assert applied_count == 1
    assert new_root == tree.get_root_hash()
    assert last_applied == 1
    assert counter == counter0 + 1
    assert ident2 == identifier

    deleted, remaining = authdb.delete_offline_operations(session)
    assert deleted == 1
    assert remaining == 0

    _root, _counter, _id, ops_after_gc = authdb.get_offline_operations(session)
    assert ops_after_gc == []


@pytest.mark.models("core")
def test_offline_sync_conflict_stops_batch_without_losing_it(session: Session) -> None:
    """Two offline edits both based on the same old_value (a real conflict):
    the first commits, the second must be rejected and stay queued for
    conflict resolution -- and GC must not delete it."""
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"", new_value=b"v1")
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"v1", new_value=b"v2")
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"v1", new_value=b"v3")

    _root, _counter, _id, ops = authdb.get_offline_operations(session)
    assert [op.sequence for op in ops] == [1, 2, 3]

    # Single-address tree: every proof is [] (single-entry MPT).
    rebased = [_rebase(op, proof=[]) for op in ops]

    applied_count, new_root, _counter, last_applied, _id = authdb.apply_offline_operations(
        session, rebased
    )
    assert applied_count == 2  # op 3 conflicts and is not applied
    assert last_applied == 2

    tree = AuthDbTree()
    tree.insert(b"alice", b"v1")
    tree.insert(b"alice", b"v2")
    assert new_root == tree.get_root_hash()

    deleted, remaining = authdb.delete_offline_operations(session)
    assert deleted == 2  # only sequences 1 and 2 were actually applied
    assert remaining == 1

    _root, _counter, _id, ops_after = authdb.get_offline_operations(session)
    assert [op.sequence for op in ops_after] == [3]  # conflicting op preserved


@pytest.mark.models("core")
def test_offline_sync_forged_mac_rejected(session: Session) -> None:
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"", new_value=b"v1")
    _root, _counter, _id, ops = authdb.get_offline_operations(session)
    op = ops[0]

    forged = authdb.RebasedOperation(
        sequence=op.sequence,
        address=op.address,
        old_value=op.old_value,
        new_value=op.new_value,
        mac=b"\x00" * 32,  # not a valid MAC for this transition
        proof=[],
    )
    applied_count, new_root, _counter, last_applied, _id = authdb.apply_offline_operations(
        session, [forged]
    )
    assert applied_count == 0
    assert new_root is None
    assert last_applied == 0


@pytest.mark.models("core")
def test_offline_sync_altered_value_after_queuing_rejected(session: Session) -> None:
    """The MAC must bind the exact new_value; substituting a different value
    (while keeping the original MAC) must be rejected, not silently applied."""
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"", new_value=b"approved")
    _root, _counter, _id, ops = authdb.get_offline_operations(session)
    op = ops[0]

    tampered = authdb.RebasedOperation(
        sequence=op.sequence,
        address=op.address,
        old_value=op.old_value,
        new_value=b"NOT_APPROVED",  # different from what was signed
        mac=op.mac,  # reused, now stale for this new_value
        proof=[],
    )
    applied_count, new_root, _counter, last_applied, _id = authdb.apply_offline_operations(
        session, [tampered]
    )
    assert applied_count == 0
    assert new_root is None
    assert last_applied == 0


@pytest.mark.models("core")
def test_offline_sync_sequence_gap_rejected(session: Session) -> None:
    """Submitting sequence 2 without sequence 1 first must be rejected --
    a host cannot skip the device forward past an un-applied operation."""
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"", new_value=b"v1")
    _seq2, _mac2, _id = authdb.queue_offline_operation(
        session, address=b"bob", old_value=b"", new_value=b"v2"
    )
    _root, _counter, _id, ops = authdb.get_offline_operations(session)
    op2 = ops[1]
    assert op2.sequence == 2

    applied_count, new_root, _counter, last_applied, _id = authdb.apply_offline_operations(
        session, [_rebase(op2, proof=[])]
    )
    assert applied_count == 0
    assert new_root is None
    assert last_applied == 0


@pytest.mark.models("core")
def test_offline_queue_capacity_enforced(session: Session) -> None:
    for n in range(64):  # MAX_OFFLINE_QUEUE_ENTRIES
        authdb.queue_offline_operation(
            session, address=b"addr-%d" % n, old_value=b"", new_value=b"val-%d" % n
        )

    with pytest.raises(TrezorFailure):
        authdb.queue_offline_operation(
            session, address=b"overflow", old_value=b"", new_value=b"val"
        )


@pytest.mark.models("core")
def test_offline_sync_delete_to_empty_tree(session: Session) -> None:
    """Regression guard: apply_offline_operations() must bump the counter
    BEFORE clearing the root on a delete-to-empty transition, since
    clear_root() deletes the identity's entire storage record (including its
    counter) and increment_counter() requires that record to still exist.
    (The sibling code path in update_leaf.py does these two calls in the
    opposite, unsafe order -- see apply_offline_operations.py for the fix.)
    """
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"", new_value=b"v1")
    _root, counter0, _id, ops = authdb.get_offline_operations(session)

    applied_count, new_root, counter1, last_applied, _id = authdb.apply_offline_operations(
        session, [_rebase(ops[0], proof=[])]
    )
    assert applied_count == 1
    assert new_root is not None
    assert counter1 == counter0 + 1

    delete_seq, delete_mac, _id = authdb.queue_offline_operation(
        session, address=b"alice", old_value=b"v1", new_value=b""
    )
    _root2, _counter2, _id2, ops2 = authdb.get_offline_operations(session)
    delete_op = [op for op in ops2 if op.sequence == delete_seq][0]

    applied_count2, new_root2, counter2, last_applied2, _id3 = authdb.apply_offline_operations(
        session, [_rebase(delete_op, proof=[])]
    )
    assert applied_count2 == 1  # must not raise / silently fail to apply
    assert new_root2 is None
    assert counter2 == counter1 + 1
    assert last_applied2 == delete_seq


@pytest.mark.models("core")
def test_offline_sync_isolated_per_identity(session: Session) -> None:
    id_a = sha256(b"sync-identity-a").digest()
    id_b = sha256(b"sync-identity-b").digest()

    authdb.set_device_id(session, id_a)
    authdb.queue_offline_operation(session, address=b"alice", old_value=b"", new_value=b"v1")
    _root, _counter, _id, ops_a = authdb.get_offline_operations(session)
    assert len(ops_a) == 1

    authdb.set_device_id(session, id_b)
    _root_b, _counter_b, _id_b, ops_b = authdb.get_offline_operations(session)
    assert ops_b == []  # no leakage from identity A's queue

    authdb.set_device_id(session, id_a)
    _root_a2, _counter_a2, _id_a2, ops_a2 = authdb.get_offline_operations(session)
    assert len(ops_a2) == 1  # identity A's queue is untouched
