"""Shared Merkle Patricia Trie hash/proof primitives.

Used by update_leaf.py, lookup.py, and apply_offline_operations.py so the
proof-verification logic is implemented and audited exactly once. See
docs/authdb.md for the hashing scheme and proof format.
"""


def sha256d(data: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


def addr_bit(addr_hash: bytes, bit: int) -> int:
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def leaf_hash(address: bytes, value: bytes) -> bytes:
    return sha256d(b"\x00" + address + value)


def internal_hash(left: bytes, right: bytes) -> bytes:
    return sha256d(b"\x01" + left + right)


def reconstruct(start_hash: bytes, proof: list, addr_hash: bytes) -> bytes:
    """Walk proof from leaf toward root, rebuilding hashes."""
    node = start_hash
    for elem in proof:
        bit = elem[0]
        sibling = bytes(elem[1:])
        if addr_bit(addr_hash, bit) == 0:
            node = internal_hash(node, sibling)
        else:
            node = internal_hash(sibling, node)
    return node


def verify_proof(
    address: bytes,
    value: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify an MPT membership proof for (address, value) against expected_root."""
    addr_hash = sha256d(address)
    node = leaf_hash(address, value)
    node = reconstruct(node, proof, addr_hash)
    return node == expected_root


def verify_nonmembership(
    address: bytes,
    witness_address: bytes,
    witness_value: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify that address is NOT in the tree.

    The caller supplies a witness leaf (witness_address, witness_value) that
    occupies address's path in the tree.  We verify:
      1. The witness is in the tree (membership proof against stored root).
      2. witness_address != address.
      3. witness_address and address share the same bit-value at every bit
         position that appears in the proof (they diverge only after the
         deepest branch, i.e. the witness is truly the closest leaf to
         address).
    """
    if witness_address == address:
        return False

    addr_hash = sha256d(address)
    witness_hash = sha256d(witness_address)

    for elem in proof:
        bit = elem[0]
        if addr_bit(addr_hash, bit) != addr_bit(witness_hash, bit):
            return False

    return verify_proof(witness_address, witness_value, proof, expected_root)
