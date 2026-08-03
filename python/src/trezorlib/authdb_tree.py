"""Merkle Patricia Trie (MPT) for WARD/AuthDB — commit-based, key-first.

Path-compressed positional trie keyed by the 32-byte ``entry_key``
(``HMAC(K_index, scope ‖ identifier)`` — see ``ward_crypto``). Leaves store the
opaque AEAD blob ``(nonce, tag, ct)``; the trie hashes only the keyless
commitment, so a host holding no keys can still hydrate and prove
(ward-design.md §2.2):

  commit   = SHA-256(0x02 || nonce || tag || len32(ct) || ct)
  leaf     = SHA-256(0x00 || entry_key || commit)
  internal = SHA-256(0x01 || left || right)          — positional, no sorting

The trie is **key-first**: every operation takes a precomputed ``entry_key``
(the device computes it; a keyless host never can). Non-membership witnesses
travel as two hashes ``(witness_entry_key, witness_commit)`` and reveal neither
the neighbour's identifier nor its plaintext value.

Proof format (leaf→root order): each element is 33 bytes, 1-byte bit-position
(0-255) + 32-byte sibling hash. O(log N).

Empty tree: ``get_root_hash()`` returns ``EMPTY_ROOT`` (all-zero); test
``is_empty()`` rather than comparing against it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from . import ward_crypto

EMPTY_ROOT: bytes = b"\x00" * 32

# stored leaf: (nonce, tag, ct, entry_type). entry_type is clear metadata (selects
# K_data on decrypt); only (nonce, tag, ct) feed the commit.
LeafBlob = Tuple[bytes, bytes, bytes, str]


def _commit(blob: LeafBlob) -> bytes:
    return ward_crypto.commit_of(blob[0], blob[1], blob[2])


def _leaf_hash(entry_key: bytes, blob: LeafBlob) -> bytes:
    return ward_crypto.leaf_hash_of(entry_key, _commit(blob))


def _addr_bit(entry_key: bytes, bit: int) -> int:
    """MSB-first: bit 0 is the most significant bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def _internal_hash(left: bytes, right: bytes) -> bytes:
    return ward_crypto.sha256(b"\x01" + left + right)


# --- internal MPT node types ---

class _LeafNode:
    __slots__ = ("addr_hash", "leaf_hash")

    def __init__(self, addr_hash: bytes, leaf_hash: bytes) -> None:
        self.addr_hash = addr_hash
        self.leaf_hash = leaf_hash


class _BranchNode:
    __slots__ = ("bit", "left", "right")

    def __init__(self, bit: int, left, right) -> None:
        self.bit = bit
        self.left = left
        self.right = right


def _find_split_bit(leaves: List[_LeafNode], start_bit: int) -> int:
    for bit in range(start_bit, 256):
        b0 = _addr_bit(leaves[0].addr_hash, bit)
        if any(_addr_bit(l.addr_hash, bit) != b0 for l in leaves[1:]):
            return bit
    raise ValueError("MPT: duplicate entry_key (HMAC-SHA256 collision)")


def _build_mpt(leaves: List[_LeafNode], start_bit: int):
    if len(leaves) == 1:
        return leaves[0]
    bit = _find_split_bit(leaves, start_bit)
    left = [l for l in leaves if _addr_bit(l.addr_hash, bit) == 0]
    right = [l for l in leaves if _addr_bit(l.addr_hash, bit) == 1]
    return _BranchNode(bit, _build_mpt(left, bit + 1), _build_mpt(right, bit + 1))


def _hash_mpt(node) -> bytes:
    if isinstance(node, _LeafNode):
        return node.leaf_hash
    return _internal_hash(_hash_mpt(node.left), _hash_mpt(node.right))


def _walk_proof(root, target_key: bytes) -> List[bytes]:
    proof: List[bytes] = []

    def walk(node) -> bytes:
        if isinstance(node, _LeafNode):
            return node.leaf_hash
        if _addr_bit(target_key, node.bit) == 0:
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


class WARDTree:
    """Commit-based, key-first MPT for WARD. Mirrors @trezor/ward proof/index.ts
    and apps.ward.service leaf/commit hashing.

    Usage::

        tree = WARDTree()
        tree.set_leaf(entry_key, nonce, tag, ct)      # entry_key from ward_crypto.entry_key(...)
        root = tree.get_root_hash()
        proof = tree.get_proof_by_key(entry_key)
        assert WARDTree.verify_proof_by_key(entry_key, nonce, tag, ct, proof, root)

        # Non-membership (witness travels as two hashes):
        proof, w_key, w_commit = tree.get_nonmembership_proof_by_key(other_key)
        assert WARDTree.verify_nonmembership_by_key(other_key, w_key, w_commit, proof, root)
    """

    # Default keys for the plaintext-convenience API when the caller does not supply
    # the device's exported keys. Fine for sync tests (the device ADOPTS the root and
    # never recomputes entry_keys); for pull/verify tests the harness MUST pass the
    # device's exported (k_index, k_data) so entry_keys match.
    _DEFAULT_SEED = b"\x2a" * 64

    def __init__(
        self, k_index: Optional[bytes] = None, k_data: Optional[bytes] = None
    ) -> None:
        self._leaves: Dict[bytes, LeafBlob] = {}
        self._k_index = k_index if k_index is not None else ward_crypto.derive_k_index(
            self._DEFAULT_SEED
        )
        # convenience k_data is per default entry_type "address"
        self._k_data = k_data if k_data is not None else ward_crypto.derive_k_data(
            self._DEFAULT_SEED, "address"
        )

    def is_empty(self) -> bool:
        return len(self._leaves) == 0

    # --- plaintext-convenience API (host/test side; keyed by the tree's k_index/k_data) ---

    def _ek(self, app_id, identifier: bytes, key_type: str, device_id: int) -> bytes:
        return ward_crypto.entry_key(self._k_index, app_id, identifier, key_type, device_id)

    def insert(
        self,
        app_id,
        identifier: bytes,
        value: bytes,
        counter: Optional[int] = None,
        key_type: str = "address",
        device_id: int = 0,
    ) -> int:
        """Insert/update (app_id, identifier)->value, encrypting the leaf with the
        tree's k_data. Empty value deletes. counter: explicit (global model) or None
        (per-entry: prev+1). Returns the new counter (0 on delete)."""
        if len(value) == 0:
            self.delete(app_id, identifier, key_type, device_id)
            return 0
        if counter is None:
            counter = self.get_counter(app_id, identifier, key_type, device_id) + 1
        ek = self._ek(app_id, identifier, key_type, device_id)
        nonce, tag, ct = ward_crypto.encrypt_leaf(
            self._k_data, ek, key_type, counter, identifier, value
        )
        self.set_leaf(ek, nonce, tag, ct, key_type)
        return counter

    def delete(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> None:
        self.del_leaf(self._ek(app_id, identifier, key_type, device_id))

    def get_counter(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> int:
        leaf = self.get_leaf(self._ek(app_id, identifier, key_type, device_id))
        if leaf is None:
            return 0
        ek = self._ek(app_id, identifier, key_type, device_id)
        c, _id, _v = ward_crypto.decrypt_leaf(self._k_data, ek, key_type, leaf[0], leaf[1], leaf[2])
        return c

    def get_value(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> bytes:
        leaf = self.get_leaf(self._ek(app_id, identifier, key_type, device_id))
        if leaf is None:
            return b""
        ek = self._ek(app_id, identifier, key_type, device_id)
        _c, _id, v = ward_crypto.decrypt_leaf(self._k_data, ek, key_type, leaf[0], leaf[1], leaf[2])
        return v

    def get_proof(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> List[bytes]:
        return self.get_proof_by_key(self._ek(app_id, identifier, key_type, device_id))

    def get_nonmembership_proof(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> Tuple[List[bytes], Optional[bytes], Optional[bytes]]:
        """Return (proof, witness_entry_key, witness_commit)."""
        return self.get_nonmembership_proof_by_key(
            self._ek(app_id, identifier, key_type, device_id)
        )

    def leaf_blob(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> Optional[LeafBlob]:
        """The stored (nonce, tag, ct, entry_type) for a membership WARDProofAck/Lookup."""
        return self.get_leaf(self._ek(app_id, identifier, key_type, device_id))

    def get_leaf(self, entry_key: bytes) -> Optional[LeafBlob]:
        """Return the stored (nonce, tag, ct, entry_type), or None if absent."""
        return self._leaves.get(entry_key)

    def set_leaf(
        self,
        entry_key: bytes,
        nonce: bytes,
        tag: bytes,
        ct: bytes,
        entry_type: str = "address",
    ) -> None:
        """Insert/update the leaf at *entry_key*. len(ct)==0 deletes it."""
        if len(ct) == 0:
            self._leaves.pop(entry_key, None)
        else:
            self._leaves[entry_key] = (nonce, tag, ct, entry_type)

    def del_leaf(self, entry_key: bytes) -> None:
        self._leaves.pop(entry_key, None)

    def _leaf_nodes(self) -> List[_LeafNode]:
        return [_LeafNode(k, _leaf_hash(k, b)) for k, b in self._leaves.items()]

    def get_root_hash(self) -> bytes:
        if not self._leaves:
            return EMPTY_ROOT
        return _hash_mpt(_build_mpt(self._leaf_nodes(), 0))

    def get_proof_by_key(self, entry_key: bytes) -> List[bytes]:
        """Membership proof (sibling hashes, leaf→root)."""
        return _walk_proof(_build_mpt(self._leaf_nodes(), 0), entry_key)

    def get_nonmembership_proof_by_key(
        self, entry_key: bytes
    ) -> Tuple[List[bytes], Optional[bytes], Optional[bytes]]:
        """Return ``(proof, witness_entry_key, witness_commit)``.

        Empty tree → ``([], None, None)``. Otherwise a membership proof for the
        witness leaf that occupies *entry_key*'s path, plus the witness's
        entry_key and commit (two hashes only)."""
        if entry_key in self._leaves:
            raise ValueError("entry_key is in the tree; use get_proof_by_key()")
        if not self._leaves:
            return [], None, None

        root_node = _build_mpt(self._leaf_nodes(), 0)
        witness: Optional[_LeafNode] = None

        def find(node) -> None:
            nonlocal witness
            if isinstance(node, _LeafNode):
                witness = node
                return
            find(node.left if _addr_bit(entry_key, node.bit) == 0 else node.right)

        find(root_node)
        assert witness is not None
        return (
            self.get_proof_by_key(witness.addr_hash),
            witness.addr_hash,
            _commit(self._leaves[witness.addr_hash]),
        )

    @staticmethod
    def verify_proof_by_key(
        entry_key: bytes,
        nonce: bytes,
        tag: bytes,
        ct: bytes,
        proof: List[bytes],
        root: bytes,
    ) -> bool:
        """Verify a membership proof for the leaf blob at *entry_key*."""
        node = ward_crypto.leaf_hash_of(entry_key, ward_crypto.commit_of(nonce, tag, ct))
        for elem in proof:
            bit, sibling = elem[0], elem[1:]
            node = _internal_hash(node, sibling) if _addr_bit(entry_key, bit) == 0 else _internal_hash(sibling, node)
        return node == root

    @staticmethod
    def verify_nonmembership_by_key(
        entry_key: bytes,
        witness_entry_key: Optional[bytes],
        witness_commit: Optional[bytes],
        proof: List[bytes],
        root: bytes,
    ) -> bool:
        """Verify *entry_key* is absent. Pass None witnesses for an empty tree."""
        if witness_entry_key is None:
            return len(proof) == 0 and root == EMPTY_ROOT
        if witness_commit is None or witness_entry_key == entry_key:
            return False
        # every branch bit in the proof must agree between target and witness
        for elem in proof:
            if _addr_bit(entry_key, elem[0]) != _addr_bit(witness_entry_key, elem[0]):
                return False
        node = ward_crypto.leaf_hash_of(witness_entry_key, witness_commit)
        for elem in proof:
            bit, sibling = elem[0], elem[1:]
            node = _internal_hash(node, sibling) if _addr_bit(witness_entry_key, bit) == 0 else _internal_hash(sibling, node)
        return node == root
