from common import unittest

from trezor.crypto.hashlib import sha256


def _sha256(data: bytes) -> bytes:
    return sha256(data).digest()


def _addr_bit(addr_hash: bytes, level: int) -> int:
    return (addr_hash[level // 8] >> (7 - level % 8)) & 1


def _leaf_hash(address: bytes, value: bytes) -> bytes:
    return _sha256(b"\x00" + address + value)


def _internal_hash(left: bytes, right: bytes) -> bytes:
    return _sha256(b"\x01" + left + right)


def _precompute_empty(depth: int) -> list:
    e = _sha256(b"")
    levels = [e]
    for _ in range(depth):
        e = _internal_hash(e, e)
        levels.append(e)
    levels.reverse()
    return levels


def build_smt_root_and_proof(entries: dict, target_address: bytes, depth: int = 32):
    """Build a Sparse Merkle Tree and return (root, proof) for target_address.

    entries: dict of address -> value
    Returns (root_hash, proof) where proof is leaf-to-root sibling hashes.
    """
    empty = _precompute_empty(depth)

    # leaves: addr_hash -> (address, value)
    leaves = {_sha256(a): (a, v) for a, v in entries.items()}

    def subtree_hash(level, lvs):
        if not lvs:
            return empty[level]
        if level == depth:
            assert len(lvs) == 1
            a, v = next(iter(lvs.values()))
            return _leaf_hash(a, v)
        left, right = {}, {}
        for ah, av in lvs.items():
            (left if _addr_bit(ah, level) == 0 else right)[ah] = av
        return _internal_hash(subtree_hash(level + 1, left), subtree_hash(level + 1, right))

    root = subtree_hash(0, leaves)

    addr_hash = _sha256(target_address)
    siblings = []
    current_lvs = dict(leaves)
    for level in range(depth):
        left, right = {}, {}
        for ah, av in current_lvs.items():
            (left if _addr_bit(ah, level) == 0 else right)[ah] = av
        bit = _addr_bit(addr_hash, level)
        if bit == 0:
            siblings.append(subtree_hash(level + 1, right))
            current_lvs = left
        else:
            siblings.append(subtree_hash(level + 1, left))
            current_lvs = right
    siblings.reverse()  # leaf-to-root

    return root, siblings


DEPTH = 32
ENTRIES = {b"alice": b"data_alice", b"bob": b"data_bob",
           b"carol": b"data_carol", b"dave": b"data_dave"}


class TestAuthDbVerifyProof(unittest.TestCase):

    def setUp(self):
        from apps.authdb.lookup import _verify_proof
        self._verify = _verify_proof

    def test_valid_proof_alice(self):
        root, proof = build_smt_root_and_proof(ENTRIES, b"alice", DEPTH)
        self.assertTrue(self._verify(b"alice", b"data_alice", proof, root))

    def test_valid_proof_bob(self):
        root, proof = build_smt_root_and_proof(ENTRIES, b"bob", DEPTH)
        self.assertTrue(self._verify(b"bob", b"data_bob", proof, root))

    def test_valid_proof_carol(self):
        root, proof = build_smt_root_and_proof(ENTRIES, b"carol", DEPTH)
        self.assertTrue(self._verify(b"carol", b"data_carol", proof, root))

    def test_invalid_wrong_value(self):
        root, proof = build_smt_root_and_proof(ENTRIES, b"alice", DEPTH)
        self.assertFalse(self._verify(b"alice", b"WRONG_VALUE", proof, root))

    def test_invalid_wrong_address(self):
        root, proof = build_smt_root_and_proof(ENTRIES, b"alice", DEPTH)
        # Use alice's proof but claim address=bob
        self.assertFalse(self._verify(b"bob", b"data_alice", proof, root))

    def test_invalid_tampered_sibling(self):
        root, proof = build_smt_root_and_proof(ENTRIES, b"alice", DEPTH)
        tampered = list(proof)
        tampered[0] = _sha256(b"garbage")
        self.assertFalse(self._verify(b"alice", b"data_alice", tampered, root))

    def test_invalid_wrong_root(self):
        _, proof = build_smt_root_and_proof(ENTRIES, b"alice", DEPTH)
        wrong_root = _sha256(b"not the root")
        self.assertFalse(self._verify(b"alice", b"data_alice", proof, wrong_root))

    def test_single_entry_tree(self):
        root, proof = build_smt_root_and_proof({b"solo": b"val"}, b"solo", DEPTH)
        self.assertTrue(self._verify(b"solo", b"val", proof, root))


if __name__ == "__main__":
    unittest.main()
