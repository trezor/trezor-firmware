"""Merkle Patricia Trie (MPT) for AuthDB.

Path-compressed positional trie. Only branches where leaves actually diverge,
so proof size is O(log N) instead of O(depth) for a fixed-depth sparse tree.

Hashing scheme (matches @trezor/ward proof/index.ts and apps.ward.service):
  entry_key  : SHA-256(app_id || 0x00 || type || 0x00 || address)   (32B, == trie path)
  value_hash : SHA-256(counter(4B BE) || value)
  leaf hash  : SHA-256(b"\\x00" + entry_key + value_hash)
  internal   : SHA-256(b"\\x01" + left + right)  — positional, no sorting

The trie is keyed by a hashed, domain-separated entry_key so entries from
different apps never collide (and a non-membership witness reveals only hashes,
never another app's plaintext identifier/value). The counter is committed inside
value_hash (never in entry_key), so an entry keeps one stable path across version
bumps. insert() supports two models: the legacy per-entry model (counter=None: 1
on first insert, +1 per update) and the global model (counter passed explicitly:
the leaf is stamped with the new global root counter on each change, matching the
current firmware).

Proof format (leaf→root order):
  Each element is 33 bytes: 1-byte bit-position (0-255) + 32-byte sibling hash.
  Proof length is O(log N) for N entries — well within the firmware buffer.

Mirrors buildMpt / generateMerkleProof / evaluateProof in merkletree.ts.

Empty tree:
  An empty WARDTree has no root hash.  get_root_hash() returns EMPTY_ROOT
  (all-zero bytes) to signal the empty state; callers should test
  ``tree.is_empty()`` rather than comparing against EMPTY_ROOT directly.
"""

from __future__ import annotations

from hashlib import sha256 as _sha256
from typing import Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Primitives (identical to merkletree.ts / apps.authdb._mpt)
# ---------------------------------------------------------------------------

EMPTY_ROOT: bytes = b"\x00" * 32


_ENTRY_TYPE_ADDRESS = "address"


def _sha256d(data: bytes) -> bytes:
    return _sha256(data).digest()


def _entry_key(
    app_id: Union[str, bytes], address: bytes, entry_type: str = _ENTRY_TYPE_ADDRESS
) -> bytes:
    """Domain-separated 32-byte trie key (== path)."""
    if isinstance(app_id, str):
        app_id = app_id.encode()
    return _sha256d(app_id + b"\x00" + entry_type.encode() + b"\x00" + address)


def _value_hash(counter: int, value: bytes) -> bytes:
    """Hiding commitment to a leaf's value (counter lives here, not in entry_key)."""
    return _sha256d(counter.to_bytes(4, "big") + value)


def _addr_bit(entry_key: bytes, bit: int) -> int:
    """MSB-first: bit 0 is the most significant bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def _leaf_hash_of(entry_key: bytes, value_hash: bytes) -> bytes:
    return _sha256d(b"\x00" + entry_key + value_hash)


def _leaf_hash(entry_key: bytes, counter: int, value: bytes) -> bytes:
    return _leaf_hash_of(entry_key, _value_hash(counter, value))


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
# WARDTree — public interface (bytes in/out, used by device tests)
# ---------------------------------------------------------------------------

class WARDTree:
    """MPT-based Merkle tree for AuthDB, keyed by a domain-separated entry_key.

    Usage::

        tree = WARDTree()
        c1 = tree.insert("bitcoin", b"alice", b"data_alice")   # c1 == 1
        c2 = tree.insert("bitcoin", b"bob",   b"data_bob")     # c2 == 1
        root = tree.get_root_hash()
        proof = tree.get_proof("bitcoin", b"alice")
        assert WARDTree.verify_proof("bitcoin", b"alice", c1, b"data_alice", proof, root)

        # UPDATE bumps the counter by exactly 1:
        c1b = tree.insert("bitcoin", b"alice", b"data_alice_v2")   # c1b == 2

        # Non-membership (witness travels as two hashes only):
        proof, w_key, w_vhash = tree.get_nonmembership_proof("bitcoin", b"unknown")
        assert WARDTree.verify_nonmembership("bitcoin", b"unknown", proof, w_key, w_vhash, root)

        # Delete (set value to empty):
        tree.delete("bitcoin", b"alice")
    """

    def __init__(self) -> None:
        # entry_key → (counter, value)
        self._leaves: Dict[bytes, Tuple[int, bytes]] = {}

    def is_empty(self) -> bool:
        return len(self._leaves) == 0

    def get_counter(self, app_id: Union[str, bytes], address: bytes) -> int:
        """Return the entry's current leaf counter, or 0 if absent."""
        entry = self._leaves.get(_entry_key(app_id, address))
        return entry[0] if entry is not None else 0

    def get_value(self, app_id: Union[str, bytes], address: bytes) -> bytes:
        """Return the entry's current value, or b"" if absent."""
        entry = self._leaves.get(_entry_key(app_id, address))
        return entry[1] if entry is not None else b""

    def insert(
        self,
        app_id: Union[str, bytes],
        address: bytes,
        value: bytes,
        counter: Optional[int] = None,
    ) -> int:
        """Insert or update the entry for *(app_id, address)*.

        Empty value is a virtual delete. Returns the new counter (0 if this
        call was a delete).

        `counter` selects the leaf-counter model:

        - Given (global model): the leaf is stamped with exactly this value.
          Callers on the global-counter model pass the new global root counter,
          matching what the device stamps on change.
        - None (legacy per-entry model): the counter becomes 1 on first insert,
          or the previous counter + 1 on every subsequent call for the same entry.
        """
        key = _entry_key(app_id, address)
        if len(value) == 0:
            self._leaves.pop(key, None)
            return 0
        if counter is None:
            existing = self._leaves.get(key)
            counter = existing[0] + 1 if existing is not None else 1
        self._leaves[key] = (counter, value)
        return counter

    def delete(self, app_id: Union[str, bytes], address: bytes) -> None:
        """Remove *(app_id, address)* (same as inserting with empty value)."""
        self._leaves.pop(_entry_key(app_id, address), None)

    def get_root_hash(self) -> bytes:
        """Return the root hash, or EMPTY_ROOT if the tree is empty."""
        if not self._leaves:
            return EMPTY_ROOT
        leaves = [
            _LeafNode(k, _leaf_hash(k, c, v)) for k, (c, v) in self._leaves.items()
        ]
        return _hash_mpt(_build_mpt(leaves, 0))

    def get_proof(self, app_id: Union[str, bytes], address: bytes) -> List[bytes]:
        """Return sibling hashes in leaf→root order.

        Each element is 33 bytes: 1-byte bit-position + 32-byte sibling hash.
        Mirrors generateMerkleProof() in @trezor/ward.
        """
        target_key = _entry_key(app_id, address)
        leaves = [
            _LeafNode(k, _leaf_hash(k, c, v)) for k, (c, v) in self._leaves.items()
        ]
        root = _build_mpt(leaves, 0)

        proof: List[bytes] = []

        def walk(node: _MptNode) -> bytes:
            if isinstance(node, _LeafNode):
                return node.leaf_hash
            target_bit = _addr_bit(target_key, node.bit)
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
        self, app_id: Union[str, bytes], address: bytes
    ) -> Tuple[List[bytes], Optional[bytes], Optional[bytes]]:
        """Return a non-membership proof for *(app_id, address)*.

        Returns ``(proof, witness_entry_key, witness_value_hash)`` — the witness is
        conveyed as two hashes only, so a querying app learns neither the witness's
        plaintext identifier nor its value.

        * If the tree is empty: ``([], None, None)``.
        * Otherwise: a membership proof for the witness leaf that occupies the
          target's path, plus the witness's entry_key and value_hash.

        Raises ValueError if *(app_id, address)* is already in the tree.
        """
        key = _entry_key(app_id, address)
        if key in self._leaves:
            raise ValueError(f"entry {address!r} is in the tree; use get_proof()")

        if not self._leaves:
            return [], None, None

        leaves = [
            _LeafNode(k, _leaf_hash(k, c, v)) for k, (c, v) in self._leaves.items()
        ]
        root_node = _build_mpt(leaves, 0)

        # Walk the tree following the target entry_key's bits until we land on a leaf
        witness_node: Optional[_LeafNode] = None

        def find_witness(node: _MptNode) -> None:
            nonlocal witness_node
            if isinstance(node, _LeafNode):
                witness_node = node
                return
            target_bit = _addr_bit(key, node.bit)
            if target_bit == 0:
                find_witness(node.left)
            else:
                find_witness(node.right)

        find_witness(root_node)
        assert witness_node is not None

        witness_key = witness_node.addr_hash
        w_counter, w_value = self._leaves[witness_key]
        proof = self._get_proof_by_key(witness_key)
        return proof, witness_key, _value_hash(w_counter, w_value)

    def _get_proof_by_key(self, target_key: bytes) -> List[bytes]:
        """get_proof, but keyed directly by an entry_key (used for the witness)."""
        leaves = [
            _LeafNode(k, _leaf_hash(k, c, v)) for k, (c, v) in self._leaves.items()
        ]
        root = _build_mpt(leaves, 0)
        proof: List[bytes] = []

        def walk(node: _MptNode) -> bytes:
            if isinstance(node, _LeafNode):
                return node.leaf_hash
            target_bit = _addr_bit(target_key, node.bit)
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
        return proof

    @staticmethod
    def verify_proof(
        app_id: Union[str, bytes],
        address: bytes,
        counter: int,
        value: bytes,
        proof: List[bytes],
        root: bytes,
    ) -> bool:
        """Verify a membership proof for *(app_id, address, counter, value)* against
        *root*. Mirrors evaluateProof() in @trezor/ward and verify_proof() in
        apps.ward.service."""
        key = _entry_key(app_id, address)
        node = _leaf_hash(key, counter, value)
        for elem in proof:
            bit = elem[0]
            sibling = elem[1:]
            if _addr_bit(key, bit) == 0:
                node = _internal_hash(node, sibling)
            else:
                node = _internal_hash(sibling, node)
        return node == root

    @staticmethod
    def verify_nonmembership(
        app_id: Union[str, bytes],
        address: bytes,
        proof: List[bytes],
        witness_entry_key: Optional[bytes],
        witness_value_hash: Optional[bytes],
        root: bytes,
    ) -> bool:
        """Verify a non-membership proof for *(app_id, address)* against *root*.

        Pass witness_entry_key=None / witness_value_hash=None for an empty tree (in
        that case root must equal EMPTY_ROOT and proof must be empty).
        """
        if witness_entry_key is None:
            return len(proof) == 0 and root == EMPTY_ROOT

        if witness_value_hash is None:
            return False

        key = _entry_key(app_id, address)

        if witness_entry_key == key:
            return False

        # All branch bits in the proof must match between target and witness keys
        for elem in proof:
            bit = elem[0]
            if _addr_bit(key, bit) != _addr_bit(witness_entry_key, bit):
                return False

        # Rebuild the witness leaf from the two hashes and check it is in the tree.
        node = _leaf_hash_of(witness_entry_key, witness_value_hash)
        for elem in proof:
            bit = elem[0]
            sibling = elem[1:]
            if _addr_bit(witness_entry_key, bit) == 0:
                node = _internal_hash(node, sibling)
            else:
                node = _internal_hash(sibling, node)
        return node == root
