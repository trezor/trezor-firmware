from common import unittest

from trezor.crypto.hashlib import sha256


def leaf_hash(value: bytes) -> bytes:
    return sha256(b"\x00" + value).digest()


def internal_hash(a: bytes, b: bytes) -> bytes:
    lo, hi = (a, b) if a <= b else (b, a)
    return sha256(b"\x01" + lo + hi).digest()


def build_root(leaves: list[bytes]) -> bytes:
    layer = list(leaves)
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else layer[i]
            next_layer.append(internal_hash(left, right))
        layer = next_layer
    return layer[0]


def build_proof(leaves: list[bytes], index: int) -> list[bytes]:
    proof = []
    layer = list(leaves)
    idx = index
    while len(layer) > 1:
        if idx % 2 == 0:
            sibling_idx = idx + 1 if idx + 1 < len(layer) else idx
        else:
            sibling_idx = idx - 1
        proof.append(layer[sibling_idx])
        next_layer = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else layer[i]
            next_layer.append(internal_hash(left, right))
        layer = next_layer
        idx //= 2
    return proof


class TestAuthDbVerifyProof(unittest.TestCase):

    def setUp(self):
        from apps.authdb.lookup import _verify_proof
        self._verify_proof = _verify_proof

        self.leaves = [leaf_hash(v.encode()) for v in ("alice", "bob", "carol", "dave")]
        self.root = build_root(self.leaves)

    def test_valid_proof_leaf_0(self):
        proof = build_proof(self.leaves, 0)
        self.assertTrue(self._verify_proof(self.leaves[0], proof, self.root))

    def test_valid_proof_leaf_1(self):
        proof = build_proof(self.leaves, 1)
        self.assertTrue(self._verify_proof(self.leaves[1], proof, self.root))

    def test_valid_proof_leaf_2(self):
        proof = build_proof(self.leaves, 2)
        self.assertTrue(self._verify_proof(self.leaves[2], proof, self.root))

    def test_valid_proof_leaf_3(self):
        proof = build_proof(self.leaves, 3)
        self.assertTrue(self._verify_proof(self.leaves[3], proof, self.root))

    def test_invalid_wrong_leaf(self):
        proof = build_proof(self.leaves, 0)
        self.assertFalse(self._verify_proof(self.leaves[1], proof, self.root))

    def test_invalid_tampered_sibling(self):
        proof = build_proof(self.leaves, 0)
        tampered = list(proof)
        tampered[0] = sha256(b"garbage").digest()
        self.assertFalse(self._verify_proof(self.leaves[0], tampered, self.root))

    def test_invalid_wrong_root(self):
        proof = build_proof(self.leaves, 0)
        wrong_root = sha256(b"not the root").digest()
        self.assertFalse(self._verify_proof(self.leaves[0], proof, wrong_root))

    def test_single_leaf_tree(self):
        lh = leaf_hash(b"solo")
        self.assertTrue(self._verify_proof(lh, [], lh))


if __name__ == "__main__":
    unittest.main()
