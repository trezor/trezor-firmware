"""Merkle Patricia Trie (MPT) for WARD/AuthDB — commit-based, key-first.

Path-compressed positional trie keyed by the 32-byte ``LeafIdentityMAC``
(``HMAC(K_path, scope ‖ identifier)`` — see ``ward_crypto``). Leaves store the
two-part ``LeafBlob`` (clear ``key_type`` plus the LeafIdentity and LeafContent
parts); the trie hashes only the keyless commitment, so a host holding no keys
can still reconstruct and prove (ward-design.md §2.2):

  commit   = SHA-256(0x02 || len8(key_type) || key_type
                          || len32(id_part) || id_part || len32(val_part) || val_part)
  leaf     = SHA-256(0x00 || LeafIdentityMAC || commit)
  internal = SHA-256(0x01 || split_bit_u16 || skiplen_u16 || left || right)
                                                    — positional, no sorting

The trie is **key-first**: every operation takes a precomputed
``LeafIdentityMAC``. A keyless host cannot *derive* one, but it does not need to
— the MAC is stored alongside the leaf, so serving proofs never needs a key.
Non-membership witnesses
travel as two hashes ``(witness_entry_key, witness_commit)`` and reveal neither
the neighbour's identifier nor its plaintext value.

Proof format (leaf→root order): each element is 36 bytes,
2-byte split_bit + 2-byte skiplen + 32-byte sibling hash. O(log N).

Empty tree: ``get_root_hash()`` returns ``EMPTY_ROOT`` (all-zero); test
``is_empty()`` rather than comparing against it.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from . import ward_crypto

EMPTY_ROOT: bytes = b"\x00" * 32

# stored leaf: ward_crypto.LeafBlob(key_type, identity: Part, content: Part).
LeafBlob = ward_crypto.LeafBlob


def _commit(blob: LeafBlob) -> bytes:
    return ward_crypto.commit_of(blob)


def _leaf_hash(entry_key: bytes, blob: LeafBlob) -> bytes:
    return ward_crypto.leaf_hash_of(entry_key, _commit(blob))


def _addr_bit(entry_key: bytes, bit: int) -> int:
    """MSB-first: bit 0 is the most significant bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def _u16be(n: int) -> bytes:
    return n.to_bytes(2, "big")


def _internal_hash(split_bit: int, skiplen: int, left: bytes, right: bytes) -> bytes:
    return ward_crypto.sha256(b"\x01" + _u16be(split_bit) + _u16be(skiplen) + left + right)


def _proof_elem(split_bit: int, skiplen: int, sibling: bytes) -> bytes:
    return _u16be(split_bit) + _u16be(skiplen) + sibling


def _parse_proof_elem(elem: bytes) -> tuple[int, int, bytes]:
    if len(elem) != 36:
        raise ValueError("invalid proof element length")
    return int.from_bytes(elem[0:2], "big"), int.from_bytes(elem[2:4], "big"), elem[4:]


# --- internal MPT node types ---

class _LeafNode:
    __slots__ = ("addr_hash", "leaf_hash")

    def __init__(self, addr_hash: bytes, leaf_hash: bytes) -> None:
        self.addr_hash = addr_hash
        self.leaf_hash = leaf_hash


class _BranchNode:
    __slots__ = ("bit", "skiplen", "left", "right")

    def __init__(self, bit: int, skiplen: int, left, right) -> None:
        self.bit = bit
        self.skiplen = skiplen
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
    skiplen = bit - start_bit
    left = [l for l in leaves if _addr_bit(l.addr_hash, bit) == 0]
    right = [l for l in leaves if _addr_bit(l.addr_hash, bit) == 1]
    return _BranchNode(
        bit, skiplen, _build_mpt(left, bit + 1), _build_mpt(right, bit + 1)
    )


def _hash_mpt(node) -> bytes:
    if isinstance(node, _LeafNode):
        return node.leaf_hash
    return _internal_hash(
        node.bit, node.skiplen, _hash_mpt(node.left), _hash_mpt(node.right)
    )


def _walk_proof(root, target_key: bytes) -> List[bytes]:
    proof: List[bytes] = []

    def walk(node) -> bytes:
        if isinstance(node, _LeafNode):
            return node.leaf_hash
        if _addr_bit(target_key, node.bit) == 0:
            left_hash = walk(node.left)
            right_hash = _hash_mpt(node.right)
            proof.append(_proof_elem(node.bit, node.skiplen, right_hash))
            return _internal_hash(node.bit, node.skiplen, left_hash, right_hash)
        else:
            left_hash = _hash_mpt(node.left)
            right_hash = walk(node.right)
            proof.append(_proof_elem(node.bit, node.skiplen, left_hash))
            return _internal_hash(node.bit, node.skiplen, left_hash, right_hash)

    walk(root)
    return proof  # post-order walk → already leaf-to-root order


def _proof_steps_root_to_leaf(proof: List[bytes]) -> Optional[List[tuple[int, int, bytes]]]:
    steps: List[tuple[int, int, bytes]] = []
    start_bit = 0
    try:
        for elem in reversed(proof):
            split_bit, skiplen, sibling = _parse_proof_elem(elem)
            if split_bit >= 256:
                return None
            if split_bit < start_bit or skiplen != split_bit - start_bit:
                return None
            steps.append((split_bit, skiplen, sibling))
            start_bit = split_bit + 1
    except ValueError:
        return None
    return steps


class WARDTree:
    """Commit-based, key-first MPT for WARD. Mirrors @trezor/ward proof/index.ts
    and apps.ward.service leaf/commit hashing.

    Usage::

        tree = WARDTree()
        tree.set_leaf(mac, leaf)      # mac from ward_crypto.leaf_identity_mac(...)
        root = tree.get_root_hash()
        proof = tree.get_proof_by_key(mac)
        assert WARDTree.verify_proof_by_key(mac, leaf, proof, root)

        # Non-membership (witness travels as two hashes):
        proof, w_key, w_commit = tree.get_nonmembership_proof_by_key(other_key)
        assert WARDTree.verify_nonmembership_by_key(other_key, w_key, w_commit, proof, root)
    """

    # Default keys for the plaintext-convenience API when the caller does not supply
    # the device's exported keys. Fine for sync tests (the device ADOPTS the root and
    # never recomputes MACs); for pull/verify tests the harness MUST pass the
    # device's (k_path, k_ident, k_data) so the MACs match.
    _DEFAULT_SEED = b"\x2a" * 64

    def __init__(
        self,
        k_path: Optional[bytes] = None,
        k_data: Optional[bytes] = None,
        k_ident: Optional[bytes] = None,
    ) -> None:
        self._leaves: Dict[bytes, LeafBlob] = {}
        seed = self._DEFAULT_SEED
        self._k_path = k_path if k_path is not None else ward_crypto.derive_k_path(seed)
        # convenience keys are for the default key_type "address"
        self._k_data = (
            k_data if k_data is not None else ward_crypto.derive_k_data(seed, "address")
        )
        self._k_ident = (
            k_ident if k_ident is not None else ward_crypto.derive_k_ident(seed, "address")
        )

    def is_empty(self) -> bool:
        return len(self._leaves) == 0

    # --- plaintext-convenience API (host/test side; keyed by the tree's k_index/k_data) ---

    def _ek(self, app_id, identifier: bytes, key_type: str, device_id: int) -> bytes:
        return ward_crypto.leaf_identity_mac(
            self._k_path, app_id, identifier, key_type, device_id
        )

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
        leaf = ward_crypto.encode_leaf(
            self._k_ident, self._k_data, ek, key_type, counter, identifier, app_id,
            value, device_id,
        )
        self.set_leaf(ek, leaf)
        return counter

    def delete(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> None:
        self.del_leaf(self._ek(app_id, identifier, key_type, device_id))

    def get_counter(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> int:
        ek = self._ek(app_id, identifier, key_type, device_id)
        leaf = self.get_leaf(ek)
        if leaf is None or leaf.content.is_empty():
            return 0
        c, _v = ward_crypto.decode_content(self._k_data, ek, key_type, leaf.content)
        return c

    def get_value(
        self, app_id, identifier: bytes, key_type: str = "address", device_id: int = 0
    ) -> bytes:
        ek = self._ek(app_id, identifier, key_type, device_id)
        leaf = self.get_leaf(ek)
        if leaf is None or leaf.content.is_empty():
            return b""
        _c, v = ward_crypto.decode_content(self._k_data, ek, key_type, leaf.content)
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
        """The stored LeafBlob for a membership WARDProofAck/Lookup."""
        return self.get_leaf(self._ek(app_id, identifier, key_type, device_id))

    def get_leaf(self, mac: bytes) -> Optional[LeafBlob]:
        """Return the stored LeafBlob, or None if absent."""
        return self._leaves.get(mac)

    def set_leaf(self, mac: bytes, leaf: LeafBlob) -> None:
        """Insert/update the leaf at *mac*. An empty content body deletes it."""
        if leaf.is_delete():
            self._leaves.pop(mac, None)
        else:
            self._leaves[mac] = leaf

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
        leaf: LeafBlob,
        proof: List[bytes],
        root: bytes,
    ) -> bool:
        """Verify a membership proof for the LeafBlob at *entry_key* (the MAC)."""
        if _proof_steps_root_to_leaf(proof) is None:
            return False
        node = ward_crypto.leaf_hash_of(entry_key, ward_crypto.commit_of(leaf))
        for elem in proof:
            split_bit, skiplen, sibling = _parse_proof_elem(elem)
            node = (
                _internal_hash(split_bit, skiplen, node, sibling)
                if _addr_bit(entry_key, split_bit) == 0
                else _internal_hash(split_bit, skiplen, sibling, node)
            )
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
        steps = _proof_steps_root_to_leaf(proof)
        if steps is None:
            return False
        # every branch bit in the proof must agree between target and witness
        for split_bit, _skiplen, _sibling in steps:
            if _addr_bit(entry_key, split_bit) != _addr_bit(witness_entry_key, split_bit):
                return False
        node = ward_crypto.leaf_hash_of(witness_entry_key, witness_commit)
        for elem in proof:
            split_bit, skiplen, sibling = _parse_proof_elem(elem)
            node = (
                _internal_hash(split_bit, skiplen, node, sibling)
                if _addr_bit(witness_entry_key, split_bit) == 0
                else _internal_hash(split_bit, skiplen, sibling, node)
            )
        return node == root
