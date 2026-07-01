from common import unittest

from trezor.crypto.hashlib import sha256


# ---------------------------------------------------------------------------
# MPT primitives (must match lookup.py and authdb_tree.py)
# ---------------------------------------------------------------------------

def _sha256d(data):
    return sha256(data).digest()


def _addr_bit(addr_hash, bit):
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def _leaf_hash(address, value):
    return _sha256d(b"\x00" + address + value)


def _internal_hash(left, right):
    return _sha256d(b"\x01" + left + right)


# ---------------------------------------------------------------------------
# MPT builder — returns (root, proof) for target_address
# ---------------------------------------------------------------------------

def _find_split_bit(leaves, start_bit):
    for bit in range(start_bit, 256):
        b0 = _addr_bit(leaves[0][0], bit)
        if any(_addr_bit(l[0], bit) != b0 for l in leaves[1:]):
            return bit
    raise ValueError("duplicate address hashes")


def _build_mpt(leaves, start_bit):
    # leaf tuple: ("leaf", addr_hash, leaf_hash)
    # branch tuple: ("branch", bit, left_node, right_node)
    if len(leaves) == 1:
        return ("leaf", leaves[0][0], leaves[0][1])
    bit = _find_split_bit(leaves, start_bit)
    left = [l for l in leaves if _addr_bit(l[0], bit) == 0]
    right = [l for l in leaves if _addr_bit(l[0], bit) == 1]
    return ("branch", bit, _build_mpt(left, bit + 1), _build_mpt(right, bit + 1))


def _hash_mpt(node):
    if node[0] == "leaf":
        return node[2]
    return _internal_hash(_hash_mpt(node[2]), _hash_mpt(node[3]))


def build_mpt_root_and_proof(entries, target_address):
    """Build an MPT and return (root_hash, proof) for target_address.

    proof is in leaf-to-root order; each element is 33 bytes:
    1-byte bit-position + 32-byte sibling hash.
    """
    leaves = [(_sha256d(a), _leaf_hash(a, v)) for a, v in entries.items()]
    root_node = _build_mpt(leaves, 0)
    root_hash = _hash_mpt(root_node)

    target_hash = _sha256d(target_address)
    proof = []

    def walk(node):
        if node[0] == "leaf":
            return node[2]
        _, bit, left, right = node
        target_bit = _addr_bit(target_hash, bit)
        if target_bit == 0:
            left_hash = walk(left)
            right_hash = _hash_mpt(right)
            proof.append(bytes([bit]) + right_hash)
            return _internal_hash(left_hash, right_hash)
        else:
            left_hash = _hash_mpt(left)
            right_hash = walk(right)
            proof.append(bytes([bit]) + left_hash)
            return _internal_hash(left_hash, right_hash)

    walk(root_node)
    return root_hash, proof   # post-order walk → leaf-to-root order


def find_witness(entries, target_address):
    """Find the witness leaf for a non-membership proof (leaf occupying target's path)."""
    target_hash = _sha256d(target_address)
    leaves = [(_sha256d(a), a, v) for a, v in entries.items()]
    root_node = _build_mpt(
        [(ah, _leaf_hash(a, v)) for ah, a, v in leaves], 0
    )
    leaf_map = {ah: (a, v) for ah, a, v in leaves}

    def walk(node):
        if node[0] == "leaf":
            return node[1]  # addr_hash of witness leaf
        _, bit, left, right = node
        if _addr_bit(target_hash, bit) == 0:
            return walk(left)
        else:
            return walk(right)

    witness_addr_hash = walk(root_node)
    return leaf_map[witness_addr_hash]  # (witness_address, witness_value)


ENTRIES = {b"alice": b"data_alice", b"bob": b"data_bob",
           b"carol": b"data_carol", b"dave": b"data_dave"}


class TestAuthDbVerifyProof(unittest.TestCase):

    def setUp(self):
        from apps.authdb.lookup import _verify_proof
        self._verify = _verify_proof

    def test_valid_proof_alice(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertTrue(self._verify(b"alice", b"data_alice", proof, root))

    def test_valid_proof_bob(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"bob")
        self.assertTrue(self._verify(b"bob", b"data_bob", proof, root))

    def test_valid_proof_carol(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"carol")
        self.assertTrue(self._verify(b"carol", b"data_carol", proof, root))

    def test_invalid_wrong_value(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify(b"alice", b"WRONG_VALUE", proof, root))

    def test_invalid_wrong_address(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        # alice's proof applied with bob's address → wrong bit decisions
        self.assertFalse(self._verify(b"bob", b"data_alice", proof, root))

    def test_invalid_tampered_sibling(self):
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        tampered = list(proof)
        tampered[0] = bytes([tampered[0][0]]) + _sha256d(b"garbage")
        self.assertFalse(self._verify(b"alice", b"data_alice", tampered, root))

    def test_invalid_wrong_root(self):
        _, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        wrong_root = _sha256d(b"not the root")
        self.assertFalse(self._verify(b"alice", b"data_alice", proof, wrong_root))

    def test_single_entry_tree(self):
        root, proof = build_mpt_root_and_proof({b"solo": b"val"}, b"solo")
        self.assertTrue(self._verify(b"solo", b"val", proof, root))
        # single-entry MPT has no branch nodes → empty proof
        self.assertEqual(proof, [])


class TestAuthDbNonMembership(unittest.TestCase):

    def setUp(self):
        from apps.authdb.lookup import _verify_nonmembership
        self._verify_nm = _verify_nonmembership

    def test_nonmember_valid(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"  # not in ENTRIES
        w_addr, w_val = find_witness(ENTRIES, target)
        proof, _ = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertTrue(self._verify_nm(target, w_addr, w_val, proof, root))

    def test_nonmember_wrong_witness_value(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_val = find_witness(ENTRIES, target)
        proof, _ = build_mpt_root_and_proof(ENTRIES, w_addr)
        self.assertFalse(self._verify_nm(target, w_addr, b"WRONG", proof, root))

    def test_nonmember_witness_equals_target_fails(self):
        # If witness_address == address, non-membership is false
        root, proof = build_mpt_root_and_proof(ENTRIES, b"alice")
        self.assertFalse(self._verify_nm(b"alice", b"alice", b"data_alice", proof, root))

    def test_nonmember_tampered_proof(self):
        root, _ = build_mpt_root_and_proof(ENTRIES, b"alice")
        target = b"zara"
        w_addr, w_val = find_witness(ENTRIES, target)
        proof, _ = build_mpt_root_and_proof(ENTRIES, w_addr)
        if proof:
            tampered = list(proof)
            tampered[0] = bytes([tampered[0][0]]) + _sha256d(b"garbage")
            self.assertFalse(self._verify_nm(target, w_addr, w_val, tampered, root))


if __name__ == "__main__":
    unittest.main()
