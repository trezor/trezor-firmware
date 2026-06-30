import pytest

from trezorlib import authdb
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.merkle_tree import MerkleTree, leaf_hash

VALUES = [b"alice", b"bob", b"carol", b"dave"]


def _make_tree() -> MerkleTree:
    return MerkleTree(VALUES)


@pytest.mark.models("core")
def test_set_root_returns_incremented_counter(session: Session) -> None:
    tree = _make_tree()
    counter1 = authdb.set_root(session, tree.get_root_hash())
    counter2 = authdb.set_root(session, tree.get_root_hash())
    assert counter2 == counter1 + 1


@pytest.mark.models("core")
@pytest.mark.parametrize("value", VALUES)
def test_lookup_valid_proof(session: Session, value: bytes) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    lhash = leaf_hash(value)
    proof = tree.get_proof(value)
    valid, counter = authdb.lookup(session, leaf_hash=lhash, proof=proof)

    assert valid is True
    assert counter > 0


@pytest.mark.models("core")
def test_lookup_invalid_proof_wrong_leaf(session: Session) -> None:
    tree = _make_tree()
    authdb.set_root(session, tree.get_root_hash())

    # Use bob's proof but alice's leaf hash – must be invalid
    lhash = leaf_hash(b"alice")
    proof = tree.get_proof(b"bob")
    valid, _counter = authdb.lookup(session, leaf_hash=lhash, proof=proof)
    assert valid is False


@pytest.mark.models("core")
def test_lookup_invalid_against_wrong_root(session: Session) -> None:
    from hashlib import sha256

    wrong_root = sha256(b"wrong").digest()
    authdb.set_root(session, wrong_root)

    tree = _make_tree()
    lhash = leaf_hash(b"alice")
    proof = tree.get_proof(b"alice")
    valid, _counter = authdb.lookup(session, leaf_hash=lhash, proof=proof)
    assert valid is False


@pytest.mark.models("core")
def test_lookup_no_root_raises(session: Session) -> None:
    from trezorlib.exceptions import TrezorFailure

    # Wipe stored root by setting a new one after a wipe – but here we just
    # use a fresh session after device wipe. In practice the emulator starts
    # clean, so issuing a lookup without ever setting a root must fail.
    lhash = leaf_hash(b"alice")
    with pytest.raises(TrezorFailure):
        authdb.lookup(session, leaf_hash=lhash, proof=[])
