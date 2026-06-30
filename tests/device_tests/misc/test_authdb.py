import pytest

from trezorlib import authdb
from trezorlib.authdb_tree import AuthDbTree
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
    counter1 = authdb.set_root(session, tree.get_root_hash())
    counter2 = authdb.set_root(session, tree.get_root_hash())
    assert counter2 == counter1 + 1


@pytest.mark.models("core")
@pytest.mark.parametrize("address,value", list(ENTRIES.items()))
def test_lookup_valid_proof(session: Session, address: bytes, value: bytes) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(address)
    valid, counter = authdb.lookup(session, address=address, value=value, proof=proof)

    assert valid is True
    assert counter > 0


@pytest.mark.models("core")
def test_lookup_invalid_wrong_value(session: Session) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    proof = tree.get_proof(b"alice")
    valid, _counter = authdb.lookup(
        session, address=b"alice", value=b"WRONG", proof=proof
    )
    assert valid is False


@pytest.mark.models("core")
def test_lookup_invalid_wrong_address(session: Session) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    # alice's proof, but claim address=bob — path mismatch
    proof = tree.get_proof(b"alice")
    valid, _counter = authdb.lookup(
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
    valid, _counter = authdb.lookup(
        session, address=b"alice", value=b"data_alice", proof=proof
    )
    assert valid is False


@pytest.mark.models("core")
def test_lookup_no_root_raises(session: Session) -> None:
    from trezorlib.exceptions import TrezorFailure

    tree = _make_tree()
    proof = tree.get_proof(b"alice")
    with pytest.raises(TrezorFailure):
        authdb.lookup(session, address=b"alice", value=b"data_alice", proof=proof)


@pytest.mark.models("core")
def test_verify_proof_host_matches_device(session: Session) -> None:
    """Confirm host-side AuthDbTree.verify_proof produces the same result as device."""
    tree = _make_tree()
    root = tree.get_root_hash()
    authdb.set_root(session, root)

    for address, value in ENTRIES.items():
        proof = tree.get_proof(address)
        host_result = AuthDbTree.verify_proof(address, value, proof, root)
        device_valid, _ = authdb.lookup(session, address=address, value=value, proof=proof)
        assert host_result == device_valid is True
