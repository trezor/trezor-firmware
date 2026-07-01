"""Merkle Patricia Trie (MPT) for AuthDB.

Path-compressed positional trie. Only branches where leaves actually diverge,
so proof size is O(log N) instead of O(depth) for a fixed-depth sparse tree.

Hashing scheme (matches merkletree.ts):
  leaf hash     : SHA-256(b"\\x00" + address + value)
  internal hash : SHA-256(b"\\x01" + left + right)  — positional, no sorting

Proof format (leaf→root order):
  Each element is 33 bytes: 1-byte bit-position (0-255) + 32-byte sibling hash.
  Proof length is O(log N) for N entries — well within the firmware buffer.

Mirrors buildMpt / generateMerkleProof / evaluateProof in merkletree.ts.

Empty tree:
  An empty AuthDbTree has no root hash.  get_root_hash() returns EMPTY_ROOT
  (all-zero bytes) to signal the empty state; callers should test
  ``tree.is_empty()`` rather than comparing against EMPTY_ROOT directly.
"""

from __future__ import annotations

from hashlib import sha256 as _sha256
from typing import Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Primitives (identical to merkletree.ts)
# ---------------------------------------------------------------------------

EMPTY_ROOT: bytes = b"\x00" * 32


def _sha256d(data: bytes) -> bytes:
    return _sha256(data).digest()


def _addr_bit(addr_hash: bytes, bit: int) -> int:
    """MSB-first: bit 0 is the most significant bit of byte 0."""
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def _leaf_hash(address: bytes, value: bytes) -> bytes:
    return _sha256d(b"\x00" + address + value)


def _internal_hash(left: bytes, right: bytes) -> bytes:
    return _sha256d(b"\x01" + left + right)


# ---------------------------------------------------------------------------
# Internal MPT node types
# ---------------------------------------------------------------------------

class _LeafNode:
    __slots__ = ("addr_hash", "leaf_hash")

    def __init__(self, addr_hash: bytes, leaf_hash: bytes) -> None:
        self.addr_hash = addr_hash
        self.leaf_hash = leaf_hash


class _BranchNode:
    __slots__ = ("bit", "left", "right")

    def __init__(self, bit: int, left: "_MptNode", right: "_MptNode") -> None:
        self.bit = bit
        self.left = left
        self.right = right


_MptNode = Union[_LeafNode, _BranchNode]


def _find_split_bit(leaves: List[_LeafNode], start_bit: int) -> int:
    """Find the first bit >= start_bit where the set of leaves diverges."""
    for bit in range(start_bit, 256):
        b0 = _addr_bit(leaves[0].addr_hash, bit)
        if any(_addr_bit(l.addr_hash, bit) != b0 for l in leaves[1:]):
            return bit
    raise ValueError("MPT: duplicate address hashes (SHA-256 collision)")


def _build_mpt(leaves: List[_LeafNode], start_bit: int) -> _MptNode:
    if len(leaves) == 1:
        return leaves[0]
    bit = _find_split_bit(leaves, start_bit)
    left = [l for l in leaves if _addr_bit(l.addr_hash, bit) == 0]
    right = [l for l in leaves if _addr_bit(l.addr_hash, bit) == 1]
    return _BranchNode(bit, _build_mpt(left, bit + 1), _build_mpt(right, bit + 1))


def _hash_mpt(node: _MptNode) -> bytes:
    if isinstance(node, _LeafNode):
        return node.leaf_hash
    return _internal_hash(_hash_mpt(node.left), _hash_mpt(node.right))


# ---------------------------------------------------------------------------
# AuthDbTree — public interface (bytes in/out, used by device tests)
# ---------------------------------------------------------------------------

class AuthDbTree:
    """MPT-based Merkle tree for AuthDB.

    Usage::

        tree = AuthDbTree()
        tree.insert(b"alice", b"data_alice")
        tree.insert(b"bob",   b"data_bob")
        root = tree.get_root_hash()
        proof = tree.get_proof(b"alice")
        assert AuthDbTree.verify_proof(b"alice", b"data_alice", proof, root)

        # Non-membership:
        proof, w_addr, w_val = tree.get_nonmembership_proof(b"unknown")
        assert AuthDbTree.verify_nonmembership(b"unknown", proof, w_addr, w_val, root)

        # Delete (set value to empty):
        tree.delete(b"alice")
    """

    def __init__(self) -> None:
        # addr_hash → (address, value)
        self._leaves: Dict[bytes, Tuple[bytes, bytes]] = {}

    def is_empty(self) -> bool:
        return len(self._leaves) == 0

    def insert(self, address: bytes, value: bytes) -> None:
        """Insert or overwrite the entry for *address*."""
        if len(value) == 0:
            # Empty value is a virtual delete
            self._leaves.pop(_sha256d(address), None)
        else:
            self._leaves[_sha256d(address)] = (address, value)

    def delete(self, address: bytes) -> None:
        """Remove *address* from the tree (same as inserting with empty value)."""
        self._leaves.pop(_sha256d(address), None)

    def get_root_hash(self) -> bytes:
        """Return the root hash, or EMPTY_ROOT if the tree is empty."""
        if not self._leaves:
            return EMPTY_ROOT
        leaves = [_LeafNode(ah, _leaf_hash(a, v)) for ah, (a, v) in self._leaves.items()]
        return _hash_mpt(_build_mpt(leaves, 0))

    def get_proof(self, address: bytes) -> List[bytes]:
        """Return sibling hashes in leaf→root order.

        Each element is 33 bytes: 1-byte bit-position + 32-byte sibling hash.
        Mirrors generateMerkleProof() in merkletree.ts.
        """
        target_addr_hash = _sha256d(address)
        leaves = [_LeafNode(ah, _leaf_hash(a, v)) for ah, (a, v) in self._leaves.items()]
        root = _build_mpt(leaves, 0)

        proof: List[bytes] = []

        def walk(node: _MptNode) -> bytes:
            if isinstance(node, _LeafNode):
                return node.leaf_hash
            target_bit = _addr_bit(target_addr_hash, node.bit)
            if target_bit == 0:
                left_hash = walk(node.left)
                right_hash = _hash_mpt(node.right)
                proof.append(bytes([node.bit]) + right_hash)
                return _internal_hash(left_hash, right_hash)
            else:
                left_hash = _hash_mpt(node.left)
                right_hash = walk(node.right)
                proof.append(bytes([node.bit]) + left_hash)
                return _internal_hash(left_hash, right_hash)

        walk(root)
        return proof  # post-order walk → already leaf-to-root order

    def get_nonmembership_proof(
        self, address: bytes
    ) -> Tuple[List[bytes], Optional[bytes], Optional[bytes]]:
        """Return a non-membership proof for *address*.

        Returns ``(proof, witness_address, witness_value)``.

        * If the tree is empty: ``([], None, None)``.
        * Otherwise: a membership proof for the witness leaf that occupies
          *address*'s path, plus the witness address and value.

        The witness leaf W is the one whose SHA-256(W) shares the longest
        common bit-prefix with SHA-256(address) — i.e. the leaf the MPT
        would land on when searching for *address*.

        Raises ValueError if *address* is already in the tree.
        """
        addr_hash = _sha256d(address)
        if addr_hash in self._leaves:
            raise ValueError(f"address {address!r} is in the tree; use get_proof()")

        if not self._leaves:
            return [], None, None

        leaves = [_LeafNode(ah, _leaf_hash(a, v)) for ah, (a, v) in self._leaves.items()]
        root_node = _build_mpt(leaves, 0)

        # Walk the tree following address's bits until we land on a leaf
        witness_node: Optional[_LeafNode] = None

        def find_witness(node: _MptNode) -> None:
            nonlocal witness_node
            if isinstance(node, _LeafNode):
                witness_node = node
                return
            target_bit = _addr_bit(addr_hash, node.bit)
            if target_bit == 0:
                find_witness(node.left)
            else:
                find_witness(node.right)

        find_witness(root_node)
        assert witness_node is not None

        witness_address, witness_value = self._leaves[witness_node.addr_hash]
        proof = self.get_proof(witness_address)
        return proof, witness_address, witness_value

    @staticmethod
    def verify_proof(
        address: bytes,
        value: bytes,
        proof: List[bytes],
        root: bytes,
    ) -> bool:
        """Verify a membership proof for *(address, value)* against *root*.

        Mirrors evaluateProof() in merkletree.ts and _verify_proof() in lookup.py.
        """
        addr_hash = _sha256d(address)
        node = _leaf_hash(address, value)
        for elem in proof:
            bit = elem[0]
            sibling = elem[1:]
            if _addr_bit(addr_hash, bit) == 0:
                node = _internal_hash(node, sibling)
            else:
                node = _internal_hash(sibling, node)
        return node == root

    @staticmethod
    def verify_nonmembership(
        address: bytes,
        proof: List[bytes],
        witness_address: Optional[bytes],
        witness_value: Optional[bytes],
        root: bytes,
    ) -> bool:
        """Verify a non-membership proof for *address* against *root*.

        Pass witness_address=None / witness_value=None for an empty tree
        (in that case root must equal EMPTY_ROOT and proof must be empty).
        """
        if witness_address is None:
            return len(proof) == 0 and root == EMPTY_ROOT

        if witness_value is None:
            return False

        addr_hash = _sha256d(address)
        witness_hash = _sha256d(witness_address)

        if witness_address == address:
            return False

        # All branch bits in the proof must match between address and witness
        for elem in proof:
            bit = elem[0]
            if _addr_bit(addr_hash, bit) != _addr_bit(witness_hash, bit):
                return False

        return AuthDbTree.verify_proof(witness_address, witness_value, proof, root)
