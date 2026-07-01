import pytest

from trezorlib import authdb
from trezorlib.authdb_tree import AuthDbTree, EMPTY_ROOT
from trezorlib.debuglink import SessionDebugWrapper as Session

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
    counter, new_root, identifier = authdb.update_leaf(
        session,
        address=b"alice",
        old_value=b"",
        new_value=b"data_alice",
        proof=[],
    )
    assert new_root is not None
    assert counter > 0
    assert identifier is not None and len(identifier) == 32
    # Host-side tree should match
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    assert new_root == tree.get_root_hash()


@pytest.mark.models("core")
def test_update_leaf_insert(session: Session) -> None:
    """INSERT: add a second entry to an existing tree."""
    # Bootstrap with alice
    counter0, root0, _ = authdb.update_leaf(
        session, address=b"alice", old_value=b"", new_value=b"data_alice", proof=[]
    )

    # Build host tree with alice to get non-membership proof for bob
    tree = AuthDbTree()
    tree.insert(b"alice", b"data_alice")
    assert tree.get_root_hash() == root0

    proof, w_addr, w_val = tree.get_nonmembership_proof(b"bob")
    counter1, new_root, identifier = authdb.update_leaf(
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
    counter, new_root, identifier = authdb.update_leaf(
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
    counter, new_root, identifier = authdb.update_leaf(
        session,
        address=b"alice",
        old_value=b"data_alice",
        new_value=b"",
        proof=proof,
    )
    assert new_root is None  # tree is empty


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
