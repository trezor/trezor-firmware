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
    internal = sha256(0x01 || u16be(split_bit) || left || right)
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
    """A wire WardLeafContent/WardLeafIdentity submessage -> its canonical framing.

    DISPATCHES ON `encoding`, NOT ON FIELD PRESENCE. This computes the commit preimage, so a
    disagreement with the firmware about which arm a message is produces a different leaf and a
    different root -- the host then serves proofs the device cannot reproduce. Presence-based
    dispatch disagreed for exactly the messages `leaf._require_canonical` now rejects: an unknown
    encoding, and both arms set at once. Those raise here too, so the two implementations refuse
    the same bytes rather than framing them differently.
    """
    if part is None:
        return bytes([1, 0, 0]) + _u32(0)  # the empty (deleted) part

    encoding = getattr(part, "encoding", None)
    encoding = 0 if encoding is None else encoding
    if encoding not in (0, 1):
        raise ValueError("unknown leaf part encoding: %r" % (encoding,))
    clear = getattr(part, "plaintext", None)
    if clear is None:
        clear = getattr(part, "plain", None)
    sealed = getattr(part, "encrypted", None)
    if sealed is not None and clear is not None:
        raise ValueError("leaf part sets both encodings")

    if encoding == 1:
        if clear is None:
            return bytes([1, 0, 0]) + _u32(0)
        # a plaintext identity carries structured fields, not a body; only the empty
        # form ever reaches the trie in practice (a delete)
        body = getattr(clear, "content", None) or b""
        return bytes([1, 0, 0]) + _u32(len(body)) + body

    if sealed is None:
        return bytes([1, 0, 0]) + _u32(0)
    nonce, tag, ct = sealed.nonce or b"", sealed.tag or b"", sealed.ct or b""
    return bytes([0, len(nonce)]) + nonce + bytes([len(tag)]) + tag + _u32(len(ct)) + ct


def commit_of(key_type: str, identity, content) -> bytes:
    kt = key_type.encode()
    a, b = _part_bytes(identity), _part_bytes(content)
    return _sha256(
        b"\x02" + bytes([len(kt)]) + kt + _u32(len(a)) + a + _u32(len(b)) + b
    )


def leaf_hash(entry_key: bytes, commit: bytes) -> bytes:
    return _sha256(b"\x00" + entry_key + commit)


def _internal(split_bit: int, left: bytes, right: bytes) -> bytes:
    return _sha256(b"\x01" + _u16(split_bit) + left + right)


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
        # THE ATTESTATION ARCHIVE: counter -> (nonce, counter, mac, timestamp, wm_signature).
        #
        # Every one of these was already received and then thrown away -- the sync helpers
        # ingested the attestation and dropped the signature. Keeping them is what makes two
        # things possible, and neither needs the WM to change:
        #
        #   ROLLBACK can prove its target was ever the head. The link into a target says a
        #   device of this wallet authorised it; only the WM's attestation says the WM held it,
        #   and without that a host may present a link from an orphaned fork.
        #
        #   CATCH-UP CAN RUN WITHOUT A LIVE ROUND. A walk anchored on an archived head proves
        #   descent in full -- an ancestor of a head the WM really held is on the authoritative
        #   line -- and claims no currency, so the device adopts and stays offline.
        #
        # The archive can only ever say "this WAS a head" -- currency still comes from a fresh,
        # nonce-bound attestation, which is the line `attest.verify_archived_attestation` keeps.
        self.attestations: dict = {}

    def archive_attestation(
        self, nonce: bytes, counter: int, mac: bytes, timestamp: int, signature: bytes
    ) -> None:
        """Keep what the WM just attested. A real host does this at every sync and publish."""
        self.attestations[counter] = (nonce, counter, mac, timestamp, signature)

    def attestation_for(self, counter: int):
        """The archived tuple for a head, or None if this host never kept one."""
        return self.attestations.get(counter)

    def links_ending_at(self, to_counter: int, to_root, limit: int = 64) -> list:
        """The predecessors of a state, NEWEST FIRST, for the device's backward walk.

        A host serving a catch-up answers exactly this question, repeatedly: "the link that ends
        at (counter, root), and then the one that ends where that one began". A real host would
        index `evolu_history` by its `to` end; here the log is short enough to scan.

        NOT A SUGGESTION THE DEVICE MAY IMPROVE ON. It refuses a link ending anywhere but the pair
        it named, so this returning the wrong branch is a refusal rather than a wrong adoption --
        which is what makes an orphaned candidate unusable even though the host holds one.
        """
        out: list = []
        counter, root = to_counter, to_root
        while len(out) < limit:
            for link in self.links:
                fc, fr, tc, tr, _ac = link
                if tc == counter and (tr or None) == (root or None):
                    out.append(link)
                    counter, root = fc, fr
                    break
            else:
                break
        return out

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
        return _internal(node[1], self._hash(node[2]), self._hash(node[3]))

    def root(self) -> Optional[bytes]:
        """None when the tree is empty -- there is no root to speak of."""
        if not self._leaves:
            return None
        return self._hash(self._build(sorted(self._leaves), 0))

    # --- proofs ---

    def _proof(self, node, target: bytes, out: list) -> bytes:
        if node[0] == "leaf":
            return self._leaves[node[1]]
        _, bit, left, right = node
        if addr_bit(target, bit) == 0:
            lh = self._proof(left, target, out)
            rh = self._hash(right)
            out.append(_u16(bit) + rh)
        else:
            lh = self._hash(left)
            rh = self._proof(right, target, out)
            out.append(_u16(bit) + lh)
        return _internal(bit, lh, rh)

    def membership_proof(self, entry_key: bytes) -> list[bytes]:
        out: list[bytes] = []
        self._proof(self._build(sorted(self._leaves), 0), entry_key, out)
        return out

    def nonmembership_proof(self, entry_key: bytes):
        """(proof, witness_entry_key, witness_commit) for a key that is absent.

        The witness is whatever leaf the lookup lands on: descend toward `entry_key` and
        take the leaf you arrive at. Its own membership proof is the absence proof.
        """
        if not self._leaves:
            return [], None, None
        node = self._build(sorted(self._leaves), 0)
        while node[0] == "branch":
            node = node[2] if addr_bit(entry_key, node[1]) == 0 else node[3]
        witness = node[1]
        return self.membership_proof(witness), witness, self._commits[witness]
