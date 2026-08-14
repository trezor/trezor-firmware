# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""A WARD trie for the host side of tests: builds the tree and serves proofs.

Unlike `ward_keys.py`, nothing here is secret-dependent -- building the trie and serving
proofs needs NO key at all, because the leaf commitment is over the encoded parts. That
is what lets a host serve proofs for entries it cannot read, and it is why this is a
faithful stand-in for a real host rather than a test-only cheat.

It is in `tests/` only because `trezorlib` has no trie yet; a real host needs exactly
this. Mirrors `core/src/apps/ward/trie.py` (verify) and the reference builder, and the
shared conformance vectors are pinned in `core/tests/test_apps.ward.py`.

    leaf     = sha256(0x00 || entry_key || commit)
    commit   = sha256(0x02 || len8(key_type) || key_type
                           || len32(id_part) || id_part || len32(val_part) || val_part)
    internal = sha256(0x01 || u16be(split_bit) || u16be(skiplen) || left || right)
    part     = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag
                            || len32(body) || body
"""

from __future__ import annotations

import hashlib
from typing import Optional

__all__ = ["WardTrie", "commit_of", "leaf_hash", "addr_bit"]


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _u16(n: int) -> bytes:
    return n.to_bytes(2, "big")


def _u32(n: int) -> bytes:
    return n.to_bytes(4, "big")


def addr_bit(entry_key: bytes, bit: int) -> int:
    """MSB-first: bit 0 is the top bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def _part_bytes(part) -> bytes:
    """A wire LeafContent/LeafIdentity submessage -> its canonical framing."""
    if part is None:
        return bytes([1, 0, 0]) + _u32(0)  # the empty (deleted) part
    if getattr(part, "plaintext", None) is not None:
        body = part.plaintext.content or b""
        return bytes([1, 0, 0]) + _u32(len(body)) + body
    if getattr(part, "plain", None) is not None:
        # a plaintext identity carries structured fields, not a body; only the empty
        # form ever reaches the trie in practice (a delete)
        return bytes([1, 0, 0]) + _u32(0)
    e = part.encrypted
    if e is None:
        return bytes([1, 0, 0]) + _u32(0)
    nonce, tag, ct = e.nonce or b"", e.tag or b"", e.ct or b""
    return (
        bytes([0, len(nonce)]) + nonce + bytes([len(tag)]) + tag + _u32(len(ct)) + ct
    )


def commit_of(key_type: str, identity, content) -> bytes:
    kt = key_type.encode()
    a, b = _part_bytes(identity), _part_bytes(content)
    return _sha256(
        b"\x02" + bytes([len(kt)]) + kt + _u32(len(a)) + a + _u32(len(b)) + b
    )


def leaf_hash(entry_key: bytes, commit: bytes) -> bytes:
    return _sha256(b"\x00" + entry_key + commit)


def _internal(split_bit: int, skiplen: int, left: bytes, right: bytes) -> bytes:
    return _sha256(b"\x01" + _u16(split_bit) + _u16(skiplen) + left + right)


class WardTrie:
    """The host's store: entry_key -> (leaf, commit), plus proof serving.

    Rebuilds the tree on every query. That is O(n log n) per call and completely wrong
    for production, but it keeps the test store obviously correct -- there is no
    incremental-update code to get subtly wrong and no cached state to go stale.
    """

    def __init__(self) -> None:
        self._leaves: dict[bytes, bytes] = {}  # entry_key -> leaf hash
        self._commits: dict[bytes, bytes] = {}  # entry_key -> commit
        self.blobs: dict[bytes, object] = {}  # entry_key -> the Leaf the device built
        # The counter the device reported for this state. A root alone does not identify
        # a moment -- roots repeat whenever contents repeat -- so a host store that keeps
        # one without the other cannot say which state it holds.
        self.counter = 0
        self.timestamp = 0
        # Ordered transitions: (from_counter, from_root, to_counter, to_root, auth_commit).
        # Opaque to the host, which is the point -- it cannot forge a step, and cannot
        # check one either; only a device of this wallet can.
        self.links: list = []

    # --- store ---

    def set(self, entry_key: bytes, leaf) -> None:
        commit = commit_of(
            (leaf.identity.key_type if leaf.identity is not None else "address"),
            leaf.identity,
            leaf.content,
        )
        self._commits[entry_key] = commit
        self._leaves[entry_key] = leaf_hash(entry_key, commit)
        self.blobs[entry_key] = leaf

    def remove(self, entry_key: bytes) -> None:
        self._leaves.pop(entry_key, None)
        self._commits.pop(entry_key, None)
        self.blobs.pop(entry_key, None)

    def __contains__(self, entry_key: bytes) -> bool:
        return entry_key in self._leaves

    def __len__(self) -> int:
        return len(self._leaves)

    # --- tree ---

    def _build(self, keys: list[bytes], start: int):
        if len(keys) == 1:
            return ("leaf", keys[0])
        bit = self._split_bit(keys, start)
        return (
            "branch",
            bit,
            bit - start,
            self._build([k for k in keys if addr_bit(k, bit) == 0], bit + 1),
            self._build([k for k in keys if addr_bit(k, bit) == 1], bit + 1),
        )

    @staticmethod
    def _split_bit(keys: list[bytes], start: int) -> int:
        for bit in range(start, 256):
            b0 = addr_bit(keys[0], bit)
            if any(addr_bit(k, bit) != b0 for k in keys[1:]):
                return bit
        raise ValueError("duplicate entry_key (HMAC-SHA256 collision)")

    def _hash(self, node) -> bytes:
        if node[0] == "leaf":
            return self._leaves[node[1]]
        return _internal(node[1], node[2], self._hash(node[3]), self._hash(node[4]))

    def root(self) -> Optional[bytes]:
        """None when the tree is empty -- there is no root to speak of."""
        if not self._leaves:
            return None
        return self._hash(self._build(sorted(self._leaves), 0))

    # --- proofs ---

    def _proof(self, node, target: bytes, out: list) -> bytes:
        if node[0] == "leaf":
            return self._leaves[node[1]]
        _, bit, skip, left, right = node
        if addr_bit(target, bit) == 0:
            lh = self._proof(left, target, out)
            rh = self._hash(right)
            out.append(_u16(bit) + _u16(skip) + rh)
        else:
            lh = self._hash(left)
            rh = self._proof(right, target, out)
            out.append(_u16(bit) + _u16(skip) + lh)
        return _internal(bit, skip, lh, rh)

    def membership_proof(self, entry_key: bytes) -> list[bytes]:
        out: list[bytes] = []
        self._proof(self._build(sorted(self._leaves), 0), entry_key, out)
        return out

    def _sibling(self, entry_key: bytes):
        """The node that a delete of `entry_key` would promote, or None if it is the last."""
        proof = self.membership_proof(entry_key)
        if not proof:
            return None
        node = self._build(sorted(self._leaves), 0)
        split0 = int.from_bytes(proof[0][0:2], "big")
        while node[0] == "branch" and node[1] != split0:
            node = node[3] if addr_bit(entry_key, node[1]) == 0 else node[4]
        return node[4] if addr_bit(entry_key, split0) == 0 else node[3]

    def sibling_decomposition(self, entry_key: bytes):
        """(split_bit, left, right) when the promoted sibling is a BRANCH, else None.

        A re-parented branch's hash is stale the moment it moves -- it commits to a skiplen
        measured from its old parent -- so the device must re-derive it at the shallower
        depth, and can only do that from its pieces. See `trie.compute_new_root`.
        """
        sibling = self._sibling(entry_key)
        if sibling is None or sibling[0] == "leaf":
            return None
        return sibling[1], self._hash(sibling[3]), self._hash(sibling[4])

    def sibling_leaf(self, entry_key: bytes):
        """(entry_key, commit) when the promoted sibling is a LEAF, else None.

        A leaf promotes exactly, having no skiplen to restate -- but the device is not
        allowed to ASSUME that from a missing decomposition, since it cannot verify an
        omission. It recomputes the leaf hash from these two values and checks it against
        the hash the proof committed to, which is what makes "it is a leaf" a fact.
        """
        sibling = self._sibling(entry_key)
        if sibling is None or sibling[0] != "leaf":
            return None
        key = sibling[1]
        return key, self._commits[key]

    def nonmembership_proof(self, entry_key: bytes):
        """(proof, witness_entry_key, witness_commit) for a key that is absent.

        The witness is whatever leaf the lookup lands on: descend toward `entry_key` and
        take the leaf you arrive at. Its own membership proof is the absence proof.
        """
        if not self._leaves:
            return [], None, None
        node = self._build(sorted(self._leaves), 0)
        while node[0] == "branch":
            node = node[3] if addr_bit(entry_key, node[1]) == 0 else node[4]
        witness = node[1]
        return self.membership_proof(witness), witness, self._commits[witness]
