# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

"""The WARD Merkle trie, host side: build it, serve proofs, and check them.

The spec is `docs/core/misc/ward-trie.md`; the firmware verifier is `core/src/apps/ward/trie.py`,
and this must stay byte-for-byte identical to it -- the conformance vectors in
`python/tests/test_ward_trie.py` are the same ones `core/tests/test_apps.ward.py` pins.

    leaf     = sha256(0x00 || entry_key || commit)
    commit   = sha256(0x02 || len8(key_type) || key_type
                           || len32(id_part) || id_part || len32(val_part) || val_part)
    internal = sha256(0x01 || u16be(split_bit) || left || right)
    empty    = sha256(0x03)
    part     = encoding(1B) || len8(nonce) || nonce || len8(tag) || tag || len32(body) || body

A path-compressed binary trie keyed by the 32-byte entry_key, MSB-first. Children are
POSITIONAL (left is bit 0), never sorted; a node's hash commits to its split bit and never to its
depth, so a subtree that moves up or down keeps its hash. A proof is a list of 34-byte elements,
LEAF-TO-ROOT, each `u16be(split_bit) || sibling`.

THREE LAYERS, usable separately:

  primitives   hashing and the proof element, exactly as the firmware computes them.
  verifier     `fold`, `check_shape`, membership, non-membership, and the roots an insert, a
               delete and an update derive -- the device's own rules, so a host can predict the
               root a write will produce and refuse to send what the device would refuse.
  store        `WardTrie`: the leaves a host holds, the proofs it serves, and its transition log.

Serving proofs needs NO key: the leaf commitment is over the encoded parts, so a host proves what
it holds without being able to read it.
"""

from __future__ import annotations

import hashlib
from typing import NamedTuple, Optional, Sequence

__all__ = [
    "EMPTY_ROOT",
    "OP_COMMIT",
    "OP_REVERT",
    "PROOF_ELEM_LEN",
    "WardTrieError",
    "addr_bit",
    "commit_of",
    "leaf_hash",
    "internal_hash",
    "proof_elem",
    "parse_proof_elem",
    "check_shape",
    "fold",
    "verify_membership",
    "verify_nonmembership",
    "insert_root",
    "delete_root",
    "update_root",
    "Link",
    "TransitionLog",
    "WardTrie",
]

# --- primitives ---------------------------------------------------------------------------------

EMPTY_ROOT = hashlib.sha256(b"\x03").digest()
"""The root of the empty tree: a value no leaf or node can take (different domain byte)."""

PROOF_ELEM_LEN = 34
_KEY_BITS = 256

# What a transition DID, recorded because it cannot be recovered -- see `TransitionLog`.
OP_COMMIT = "commit"
OP_REVERT = "revert"


class WardTrieError(ValueError):
    """A malformed operand or proof, or a claim that does not hold. What the device raises too."""


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _u16(n: int) -> bytes:
    return n.to_bytes(2, "big")


def _u32(n: int) -> bytes:
    return n.to_bytes(4, "big")


def _require32(*values: bytes) -> None:
    # Every opaque operand is exactly 32 bytes, and that is load-bearing: the preimages
    # concatenate them with no separator, so a key K || C[0] with commit C[1:] hashes to the
    # leaf of (K, C). Fixed width makes every split unambiguous.
    for v in values:
        if v is None or len(v) != 32:
            raise WardTrieError("WARD trie operands must be 32 bytes")


def addr_bit(entry_key: bytes, bit: int) -> int:
    """Bit `bit` of the path, MSB-first: bit 0 is the top bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def _part_bytes(part: object) -> bytes:
    """A wire WardLeafContent/WardLeafIdentity submessage -> its canonical framing.

    DISPATCHES ON `encoding`, NOT ON FIELD PRESENCE. This computes the commit preimage, so a
    disagreement with the firmware about which arm a message is produces a different leaf and a
    different root -- the host then serves proofs the device cannot reproduce. Presence-based
    dispatch disagreed for exactly the messages `leaf._require_canonical` rejects: an unknown
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


def commit_of(key_type: str, identity: object, content: object) -> bytes:
    """The leaf commitment over a leaf's wire parts. `identity`/`content` may be None (empty)."""
    kt = key_type.encode()
    a, b = _part_bytes(identity), _part_bytes(content)
    return _sha256(b"\x02" + bytes([len(kt)]) + kt + _u32(len(a)) + a + _u32(len(b)) + b)


def leaf_hash(entry_key: bytes, commit: bytes) -> bytes:
    """leaf = sha256(0x00 || entry_key || commit), both exactly 32 bytes."""
    _require32(entry_key, commit)
    return _sha256(b"\x00" + entry_key + commit)


def internal_hash(split_bit: int, left: bytes, right: bytes) -> bytes:
    """internal = sha256(0x01 || u16be(split_bit) || left || right). Children are positional."""
    return _sha256(b"\x01" + _u16(split_bit) + left + right)


def proof_elem(split_bit: int, sibling: bytes) -> bytes:
    """One proof element: u16be(split_bit) || sibling(32B)."""
    _require32(sibling)
    return _u16(split_bit) + sibling


def parse_proof_elem(elem: bytes) -> tuple[int, bytes]:
    """(split_bit, sibling). Exactly 34 bytes, or a sibling of the wrong width would shift the
    next node's preimage."""
    if len(elem) != PROOF_ELEM_LEN:
        raise WardTrieError("invalid proof element length")
    return int.from_bytes(elem[0:2], "big"), bytes(elem[2:])


# --- verifier: the device's own rules ------------------------------------------------------------


def check_shape(proof: Sequence[bytes]) -> list[tuple[int, bytes]]:
    """Refuse a proof that is not a real root-to-leaf path; return its parsed steps.

    Read root-first (the proof reversed), split bits must strictly increase and stay below 256 --
    which also caps a valid proof at 256 elements. It cannot check canonicity: one path does not
    show what the siblings hold. The device keeps trees canonical by building them that way.
    """
    steps = []
    prev = -1
    for elem in reversed(proof):
        split_bit, sibling = parse_proof_elem(elem)
        if split_bit >= _KEY_BITS:
            raise WardTrieError("proof split_bit out of range")
        if split_bit <= prev:
            raise WardTrieError("proof split bits are not strictly increasing")
        steps.append((split_bit, sibling))
        prev = split_bit
    return steps


def fold(start: bytes, proof: Sequence[bytes], entry_key: bytes) -> bytes:
    """Hash `start` up the path of `entry_key` to a CANDIDATE root.

    `start` is a leaf or any subtree's hash. The result proves nothing until compared with a root
    the caller already trusts -- a proof checked against a root the host also supplied is theatre.
    """
    _require32(start, entry_key)
    check_shape(proof)
    node = start
    for elem in proof:
        split_bit, sibling = parse_proof_elem(elem)
        if addr_bit(entry_key, split_bit) == 0:
            node = internal_hash(split_bit, node, sibling)
        else:
            node = internal_hash(split_bit, sibling, node)
    return node


def verify_membership(
    entry_key: bytes, commit: bytes, proof: Sequence[bytes], root: bytes
) -> bool:
    """Is the leaf `(entry_key, commit)` in the tree with this root?"""
    return fold(leaf_hash(entry_key, commit), proof, entry_key) == root


def _absence_failure(
    entry_key: bytes,
    witness_key: bytes,
    witness_commit: bytes,
    proof: Sequence[bytes],
    root: bytes,
) -> Optional[str]:
    # Widths RAISE; every other failure is a reason. The same split as the firmware.
    _require32(entry_key, witness_key, witness_commit)
    if witness_key == entry_key:
        return "witness must differ from entry_key"
    for split_bit, _sibling in check_shape(proof):
        if addr_bit(entry_key, split_bit) != addr_bit(witness_key, split_bit):
            return "witness does not occupy the target's path"
    if fold(leaf_hash(witness_key, witness_commit), proof, witness_key) != root:
        return "witness is not in the tree"
    return None


def verify_nonmembership(
    entry_key: bytes,
    witness_key: bytes,
    witness_commit: bytes,
    proof: Sequence[bytes],
    root: bytes,
) -> bool:
    """Is `entry_key` absent? Shown by the leaf that occupies its path. Raises on bad widths."""
    return _absence_failure(entry_key, witness_key, witness_commit, proof, root) is None


def _require_settled(stored_root: Optional[bytes]) -> bytes:
    # None is "cannot verify", never "empty": read as empty it would authorise a witness-less
    # insert that replaces the tree. The caller settles it -- see the firmware's `root_for_write`.
    if stored_root is None:
        raise WardTrieError("no trusted root")
    return stored_root


def insert_root(
    entry_key: bytes,
    new_commit: bytes,
    proof: Sequence[bytes],
    stored_root: bytes,
    witness_key: Optional[bytes] = None,
    witness_commit: Optional[bytes] = None,
) -> bytes:
    """The root after inserting `(entry_key, new_commit)`, having proved `entry_key` absent."""
    stored_root = _require_settled(stored_root)
    _require32(entry_key)

    if stored_root == EMPTY_ROOT:
        # The first entry of an empty tree: the device's OWN record is the only authority.
        if proof or witness_key is not None:
            raise WardTrieError("an empty tree takes no witness")
        return leaf_hash(entry_key, new_commit)
    if witness_key is None or witness_commit is None:
        raise WardTrieError("insert needs a non-membership witness")

    failure = _absence_failure(entry_key, witness_key, witness_commit, proof, stored_root)
    if failure is not None:
        raise WardTrieError(failure)

    # The splice point is derived, never taken from anyone: the first bit where the keys part.
    split_bit = next(
        b for b in range(_KEY_BITS) if addr_bit(entry_key, b) != addr_bit(witness_key, b)
    )
    idx = 0
    while idx < len(proof) and parse_proof_elem(proof[idx])[0] > split_bit:
        idx += 1
    if idx < len(proof) and parse_proof_elem(proof[idx])[0] == split_bit:
        raise WardTrieError("witness path already branches at the split bit")

    # Everything below the splice folds into one node, which moves up with its hash unchanged.
    subtree = fold(leaf_hash(witness_key, witness_commit), proof[:idx], witness_key)
    new_h = leaf_hash(entry_key, new_commit)
    if addr_bit(entry_key, split_bit) == 0:
        branch = internal_hash(split_bit, new_h, subtree)
    else:
        branch = internal_hash(split_bit, subtree, new_h)
    # Above the splice both keys agree at every branch bit: either path folds the same.
    return fold(branch, proof[idx:], witness_key)


def _prove_present(
    entry_key: bytes, old_commit: bytes, proof: Sequence[bytes], stored_root: bytes
) -> None:
    stored_root = _require_settled(stored_root)
    if stored_root == EMPTY_ROOT:
        raise WardTrieError("the tree is empty; nothing to replace")
    if not verify_membership(entry_key, old_commit, proof, stored_root):
        raise WardTrieError("current entry does not match the trusted root")


def delete_root(
    entry_key: bytes, old_commit: bytes, proof: Sequence[bytes], stored_root: bytes
) -> bytes:
    """The root after deleting a present leaf: its sibling moves up unchanged. EMPTY_ROOT if last."""
    _prove_present(entry_key, old_commit, proof, stored_root)
    if not proof:
        return EMPTY_ROOT
    _split_bit, sibling = parse_proof_elem(proof[0])
    return fold(sibling, proof[1:], entry_key)


def update_root(
    entry_key: bytes,
    old_commit: bytes,
    new_commit: bytes,
    proof: Sequence[bytes],
    stored_root: bytes,
) -> bytes:
    """The root after replacing a present leaf's value: same path, same siblings, new leaf."""
    _prove_present(entry_key, old_commit, proof, stored_root)
    return fold(leaf_hash(entry_key, new_commit), proof, entry_key)


# --- store: the transition log ---------------------------------------------------------------


class Link(NamedTuple):
    """One transition in a wallet's history, as a host logs it.

    The first five fields are opaque to the host, which is the point -- it cannot forge a step, and
    cannot check one either; only a device of this wallet can. A NamedTuple, so existing code that
    indexes (`link[4]`) or slices (`link[:5]`) the old 6-tuple keeps working.
    """

    from_counter: int
    from_root: Optional[bytes]
    to_counter: int
    to_root: Optional[bytes]
    auth_commit: bytes
    operation: str


class TransitionLog:
    """What a host keeps so other devices of the wallet can walk the steps they missed.

    THE OPERATION HAS TO BE RECORDED RATHER THAN DERIVED. Whether a link is a COMMIT or a REVERT is
    decided by which tag its `auth_commit` was minted under, and recovering that means computing
    the MAC both ways under K_auth -- which the host does not have and must never have. So it is
    free at creation and unrecoverable afterwards.

    `wm_sigs` maps a counter to the device's `wm_sig` for the transition that REACHED it: a link is
    folded by another DEVICE, a `wm_sig` is handed to the WM, so they have different audiences. A
    host that lost these cannot advance the WM's head, which is the intended failure.

    NO ATTESTATION ARCHIVE. Nothing reads an archived attestation any more -- anchoring a walk on
    one raised the persisted counter with no freshness -- so nothing keeps one.
    """

    def __init__(self) -> None:
        self.links: list = []
        self.wm_sigs: dict = {}

    def record(
        self,
        from_counter: int,
        from_root: Optional[bytes],
        to_counter: int,
        to_root: Optional[bytes],
        auth_commit: bytes,
        operation: str = OP_COMMIT,
        wm_sig: Optional[bytes] = None,
    ) -> Link:
        """Append one transition (and its `wm_sig`, if the host holds one)."""
        if operation not in (OP_COMMIT, OP_REVERT):
            raise ValueError("unknown link operation: %r" % (operation,))
        link = Link(from_counter, from_root, to_counter, to_root, auth_commit, operation)
        self.links.append(link)
        if wm_sig is not None:
            self.wm_sigs[to_counter] = wm_sig
        return link

    def links_ending_at(
        self, to_counter: int, to_root: Optional[bytes], limit: int = 64
    ) -> list:
        """The predecessors of a state, walking BACK from it -- the device's backward walk.

        THE NEWEST MATCH WINS where several rows end at the same `(counter, root)`: a counter can
        be reached TWICE once a demotion exists, and the later edge is the live history. The device
        refuses a link ending anywhere but the pair it named, so a wrong answer here is a refusal
        rather than a wrong adoption.
        """
        out: list = []
        counter, root = to_counter, to_root
        while len(out) < limit:
            for link in reversed(self.links):
                if link[2] == counter and (link[3] or None) == (root or None):
                    out.append(link)
                    counter, root = link[0], link[1]
                    break
            else:
                break
        return out

    def fork_point(self, a: tuple, b: tuple) -> Optional[int]:
        """The last counter two `(counter, root)` states share, walking both back; None if never.

        What a host passes as `WardRejoin.fork_counter`. The device checks it rather than trusting
        it, so a wrong answer here is a refusal, not a wrong rejoin.
        """
        (ac, ar), (bc, br) = a, b
        while (ac, ar or None) != (bc, br or None):
            if ac >= bc:
                prev = self.links_ending_at(ac, ar, limit=1)
                if not prev:
                    return None
                ac, ar = prev[0][0], prev[0][1]
            else:
                prev = self.links_ending_at(bc, br, limit=1)
                if not prev:
                    return None
                bc, br = prev[0][0], prev[0][1]
        return ac


# --- store: the tree ---------------------------------------------------------------------------


class WardTrie(TransitionLog):
    """A host's replica: entry_key -> leaf, the canonical root, proofs -- and its transition log.

    CACHED, WITH THE REBUILD AS THE ORACLE. The tree is built once and reused until a leaf changes;
    `set` and `remove` are the only mutators and both drop it. `rebuild_root()` recomputes from
    scratch, and the tests assert the two always agree -- so the cache is an optimisation with a
    check, not a second implementation to trust.

    `root()` is None for an empty tree, because that is what goes on the wire ("absent"); the
    preimage form, and what the verifier functions take, is `root_or_empty()`.
    """

    def __init__(self) -> None:
        super().__init__()
        self._leaves: dict[bytes, bytes] = {}  # entry_key -> leaf hash
        self._commits: dict[bytes, bytes] = {}  # entry_key -> commit
        self.blobs: dict[bytes, object] = {}  # entry_key -> the Leaf the device built
        self._tree = None
        # The counter the device reported for this state. A root alone does not identify a
        # moment -- roots repeat whenever contents repeat -- so a store that kept one without the
        # other could not say which state it holds.
        self.counter = 0
        self.timestamp = 0

    # --- leaves ---

    def set(self, entry_key: bytes, leaf: object, key_type: Optional[str] = None) -> None:
        """Store the leaf the device built. `key_type` defaults to the one its identity names.

        The key_type is inside the commitment, so it must be the one the device used; a leaf
        without an identity part has nothing to name it, and `key_type` has to be passed.
        """
        if key_type is None:
            if leaf.identity is None or getattr(leaf.identity, "key_type", None) is None:
                # the historical default for identity-less leaves, kept so fixtures that build
                # bare content leaves still hash as the firmware does
                key_type = "address"
            else:
                key_type = leaf.identity.key_type
        commit = commit_of(key_type, leaf.identity, leaf.content)
        self._commits[entry_key] = commit
        self._leaves[entry_key] = leaf_hash(entry_key, commit)
        self.blobs[entry_key] = leaf
        self._tree = None

    def remove(self, entry_key: bytes) -> None:
        self._leaves.pop(entry_key, None)
        self._commits.pop(entry_key, None)
        self.blobs.pop(entry_key, None)
        self._tree = None

    def scratch(self, staged: Sequence[tuple] = ()) -> "WardTrie":
        """A copy of the tree with `staged` (entry_key, commit) leaves applied -- no log, no blobs
        for the staged keys.

        What a host serves a BATCHED flush from: the device proves each change against the root it
        has built so far, which already holds the changes it folded before, and this is that tree.
        The store itself is untouched until the batch is applied.
        """
        copy = WardTrie()
        copy._leaves = dict(self._leaves)
        copy._commits = dict(self._commits)
        copy.blobs = dict(self.blobs)
        for entry_key, commit in staged:
            copy._commits[entry_key] = commit
            copy._leaves[entry_key] = leaf_hash(entry_key, commit)
        copy.counter = self.counter
        return copy

    def commit(self, entry_key: bytes) -> bytes:
        return self._commits[entry_key]

    def __contains__(self, entry_key: bytes) -> bool:
        return entry_key in self._leaves

    def __len__(self) -> int:
        return len(self._leaves)

    # --- tree ---

    def _build(self, keys: list, start: int) -> tuple:
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
    def _split_bit(keys: list, start: int) -> int:
        # The FIRST bit on which the keys diverge -- canonicity is exactly this choice.
        for bit in range(start, _KEY_BITS):
            b0 = addr_bit(keys[0], bit)
            if any(addr_bit(k, bit) != b0 for k in keys[1:]):
                return bit
        raise ValueError("duplicate entry_key (HMAC-SHA256 collision)")

    def _hash(self, node: tuple) -> bytes:
        if node[0] == "leaf":
            return self._leaves[node[1]]
        return internal_hash(node[1], self._hash(node[2]), self._hash(node[3]))

    def _root_node(self) -> tuple:
        if self._tree is None:
            self._tree = self._build(sorted(self._leaves), 0)
        return self._tree

    def root(self) -> Optional[bytes]:
        """The canonical root, or None when the tree is empty (the wire's "absent")."""
        if not self._leaves:
            return None
        return self._hash(self._root_node())

    def root_or_empty(self) -> bytes:
        """The root in preimage form: EMPTY_ROOT for the empty tree."""
        root = self.root()
        return EMPTY_ROOT if root is None else root

    def rebuild_root(self) -> Optional[bytes]:
        """The root recomputed from scratch, ignoring the cache: the oracle `root()` is held to."""
        if not self._leaves:
            return None
        return self._hash(self._build(sorted(self._leaves), 0))

    # --- proofs ---

    def _proof(self, node: tuple, target: bytes, out: list) -> bytes:
        if node[0] == "leaf":
            return self._leaves[node[1]]
        _, bit, left, right = node
        if addr_bit(target, bit) == 0:
            lh = self._proof(left, target, out)
            rh = self._hash(right)
            out.append(proof_elem(bit, rh))
        else:
            lh = self._hash(left)
            rh = self._proof(right, target, out)
            out.append(proof_elem(bit, lh))
        return internal_hash(bit, lh, rh)

    def membership_proof(self, entry_key: bytes) -> list:
        """The proof for a PRESENT key, leaf-to-root."""
        if entry_key not in self._leaves:
            raise KeyError("entry_key is not in the tree")
        out: list = []
        self._proof(self._root_node(), entry_key, out)
        return out

    def nonmembership_proof(
        self, entry_key: bytes
    ) -> tuple[list, Optional[bytes], Optional[bytes]]:
        """(proof, witness_entry_key, witness_commit) for an ABSENT key; ([], None, None) if empty.

        The witness is whatever leaf the lookup lands on: descend toward `entry_key` and take the
        leaf you arrive at. Its own membership proof is the absence proof.
        """
        if not self._leaves:
            return [], None, None
        node = self._root_node()
        while node[0] == "branch":
            node = node[2] if addr_bit(entry_key, node[1]) == 0 else node[3]
        witness = node[1]
        return self.membership_proof(witness), witness, self._commits[witness]
