"""Sparse Merkle Tree for AuthDB.

Path routing is determined by bits of SHA-256(address), MSB first, so left/right
at each level is fixed by the address — independent of the leaf value.

Hashing scheme:
  leaf hash     : SHA-256(b"\\x00" + address + value)
  internal hash : SHA-256(b"\\x01" + left + right)   — positional, no min/max
  empty leaf    : SHA-256(b"")
  empty subtree : propagated upward via internal_hash(empty, empty)
"""

from __future__ import annotations

from hashlib import sha256 as _sha256
from typing import Dict, List, Optional, Tuple

DEFAULT_DEPTH = 32  # 2^32 address space; proof = 32 × 32 B = 1 KB


# ---------------------------------------------------------------------------
# Primitive hash functions
# ---------------------------------------------------------------------------

def authdb_leaf_hash(address: bytes, value: bytes) -> bytes:
    return _sha256(b"\x00" + address + value).digest()


def authdb_internal_hash(left: bytes, right: bytes) -> bytes:
    return _sha256(b"\x01" + left + right).digest()


def _addr_bit(addr_hash: bytes, level: int) -> int:
    """Return bit `level` (MSB first) of `addr_hash`."""
    return (addr_hash[level // 8] >> (7 - level % 8)) & 1


def _precompute_empty(depth: int) -> List[bytes]:
    """Return list of length depth+1 where empty[i] is the hash of an all-empty
    subtree at tree level i (0 = root, depth = leaf level)."""
    e = _sha256(b"").digest()   # empty leaf
    levels = [e]
    for _ in range(depth):
        e = authdb_internal_hash(e, e)
        levels.append(e)
    levels.reverse()            # index 0 → root level
    return levels


# ---------------------------------------------------------------------------
# AuthDbTree
# ---------------------------------------------------------------------------

_LeafMap = Dict[bytes, Tuple[bytes, bytes]]   # addr_hash → (address, value)


class AuthDbTree:
    """Sparse Merkle Tree where each leaf's position is determined by
    SHA-256(address) bit-path, not by sorting leaf values.

    Usage::

        tree = AuthDbTree()
        tree.insert(b"alice", b"data_alice")
        tree.insert(b"bob",   b"data_bob")
        root = tree.get_root_hash()
        proof = tree.get_proof(b"alice")
        assert tree.verify_proof(b"alice", b"data_alice", proof, root)
    """

    def __init__(self, depth: int = DEFAULT_DEPTH) -> None:
        self.depth = depth
        self._leaves: _LeafMap = {}
        self._empty = _precompute_empty(depth)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def insert(self, address: bytes, value: bytes) -> None:
        """Insert or overwrite the entry for *address*."""
        addr_hash = _sha256(address).digest()
        self._leaves[addr_hash] = (address, value)

    def get_root_hash(self) -> bytes:
        return self._subtree_hash(0, self._leaves)

    def get_proof(self, address: bytes) -> List[bytes]:
        """Return sibling hashes ordered from *leaf level up to root*
        (proof[0] is the sibling nearest the leaf).

        Compatible with :func:`verify_proof` and the firmware verifier.
        """
        addr_hash = _sha256(address).digest()
        siblings: List[bytes] = []
        leaves = dict(self._leaves)

        for level in range(self.depth):
            left, right = self._split(leaves, level)
            bit = _addr_bit(addr_hash, level)
            if bit == 0:
                # current node is in left subtree; sibling is right subtree
                siblings.append(self._subtree_hash(level + 1, right))
                leaves = left
            else:
                siblings.append(self._subtree_hash(level + 1, left))
                leaves = right

        siblings.reverse()   # leaf-to-root order
        return siblings

    @staticmethod
    def verify_proof(
        address: bytes,
        value: bytes,
        proof: List[bytes],
        root: bytes,
    ) -> bool:
        """Verify a Merkle proof for *(address, value)* against *root*.

        *proof* must be in leaf-to-root order, as returned by :meth:`get_proof`.
        """
        addr_hash = _sha256(address).digest()
        current = authdb_leaf_hash(address, value)
        depth = len(proof)
        for i, sibling in enumerate(proof):
            level = depth - 1 - i          # 0 = root level, depth-1 = leaf level
            bit = _addr_bit(addr_hash, level)
            if bit == 0:
                current = authdb_internal_hash(current, sibling)
            else:
                current = authdb_internal_hash(sibling, current)
        return current == root

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _subtree_hash(self, level: int, leaves: _LeafMap) -> bytes:
        if not leaves:
            return self._empty[level]
        if level == self.depth:
            assert len(leaves) == 1, "hash collision in address space"
            addr, val = next(iter(leaves.values()))
            return authdb_leaf_hash(addr, val)
        left, right = self._split(leaves, level)
        return authdb_internal_hash(
            self._subtree_hash(level + 1, left),
            self._subtree_hash(level + 1, right),
        )

    @staticmethod
    def _split(leaves: _LeafMap, level: int) -> Tuple[_LeafMap, _LeafMap]:
        """Partition *leaves* by bit *level* of their address hash."""
        left: _LeafMap = {}
        right: _LeafMap = {}
        for addr_hash, av in leaves.items():
            if _addr_bit(addr_hash, level) == 0:
                left[addr_hash] = av
            else:
                right[addr_hash] = av
        return left, right


# ---------------------------------------------------------------------------
# Convenience top-level verifier (mirrors firmware logic)
# ---------------------------------------------------------------------------

def verify_proof(
    address: bytes,
    value: bytes,
    proof: List[bytes],
    root: bytes,
) -> bool:
    """Standalone proof verifier — no tree object needed."""
    return AuthDbTree.verify_proof(address, value, proof, root)
