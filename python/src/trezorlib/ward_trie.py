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

Spec: `docs/ward/ward-trie.md`. Must stay byte-for-byte identical to the firmware's
`core/src/apps/ward/trie.py`; the conformance vectors in `python/tests/test_ward_trie.py` pin both.

    leaf     = sha256(0x00 || entry_key || commit)
    commit   = value_digest = sha256(0x03 || sealed_content)      -- docs/ward/ward-leaf.md
    internal = sha256(0x01 || u8(split_bit) || left || right)
    empty    = sha256(0x02)

A path-compressed binary trie keyed MSB-first by the 32-byte entry_key; children are positional and
a node's hash commits to its split bit, never its depth. A proof is a LEAF-TO-ROOT list of 33-byte
`u8(split_bit) || sibling` elements. Serving proofs needs no key.
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
    "value_digest",
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

EMPTY_ROOT = hashlib.sha256(b"\x02").digest()
"""The root of the empty tree: a value no leaf or node can take (different domain byte)."""

PROOF_ELEM_LEN = 33
_KEY_BITS = 256

# What a transition DID, recorded because it cannot be recovered -- see `TransitionLog`.
OP_COMMIT = "commit"
OP_REVERT = "revert"


class WardTrieError(ValueError):
    """A malformed operand or proof, or a claim that does not hold. What the device raises too."""


def _sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _bit_pos(n: int) -> bytes:
    """A split bit in one byte: every position of a 256-bit key (`rust/trezor-ward`'s BitPos)."""
    return bytes([n])


def _lp(width: int, data: bytes) -> bytes:
    """`len(data)` in `width` big-endian bytes, then `data`."""
    if len(data) >> (8 * width):
        raise ValueError("bytes must be in range(0, 256)")
    return len(data).to_bytes(width, "big") + data


def _state(counter: int, root: Optional[bytes]) -> tuple:
    """A `(counter, root)` state, the empty tree as None, so states compare as states."""
    return counter, root or None


def _require32(*values: bytes) -> None:
    # Load-bearing: preimages concatenate operands with no separator, so only a fixed width
    # makes every split unambiguous.
    for v in values:
        if v is None or len(v) != 32:
            raise WardTrieError("WARD trie operands must be 32 bytes")


def addr_bit(entry_key: bytes, bit: int) -> int:
    """Bit `bit` of the path, MSB-first: bit 0 is the top bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def value_digest(sealed_content: bytes) -> bytes:
    """The leaf commitment: sha256(0x03 || sealed_content), over sealed bytes only, so a host
    with no keys can compute it. The identity is not committed; entry_key authenticates it."""
    return _sha256(b"\x03" + sealed_content)


def leaf_hash(entry_key: bytes, commit: bytes) -> bytes:
    """leaf = sha256(0x00 || entry_key || commit), both exactly 32 bytes."""
    _require32(entry_key, commit)
    return _sha256(b"\x00" + entry_key + commit)


def internal_hash(split_bit: int, left: bytes, right: bytes) -> bytes:
    """internal = sha256(0x01 || u8(split_bit) || left || right). Children are positional."""
    return _sha256(b"\x01" + _bit_pos(split_bit) + left + right)


def _join(split_bit: int, side: int, node: bytes, sibling: bytes) -> bytes:
    """The parent of `node`, which sits on `side` (its key's bit) of `split_bit`."""
    if side == 0:
        return internal_hash(split_bit, node, sibling)
    return internal_hash(split_bit, sibling, node)


def proof_elem(split_bit: int, sibling: bytes) -> bytes:
    """One proof element: u8(split_bit) || sibling(32B)."""
    _require32(sibling)
    return _bit_pos(split_bit) + sibling


def parse_proof_elem(elem: bytes) -> tuple[int, bytes]:
    """(split_bit, sibling). Exactly 33 bytes, or a sibling of the wrong width would shift the
    next node's preimage."""
    if len(elem) != PROOF_ELEM_LEN:
        raise WardTrieError("invalid proof element length")
    return elem[0], bytes(elem[1:])


# --- verifier: the device's own rules ------------------------------------------------------------


def check_shape(proof: Sequence[bytes]) -> list[tuple[int, bytes]]:
    """Refuse a proof that is not a real root-to-leaf path; return its parsed steps.

    Root-first, split bits must strictly increase and stay below 256. Canonicity is not checkable
    from one path; the device keeps trees canonical by building them that way.
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
    """Hash `start` (a leaf or subtree hash) up the path of `entry_key` to a CANDIDATE root,
    which proves nothing until compared with a root the caller already trusts."""
    _require32(start, entry_key)
    node = start
    for split_bit, sibling in reversed(check_shape(proof)):
        node = _join(split_bit, addr_bit(entry_key, split_bit), node, sibling)
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
    # insert that replaces the tree.
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
    branch = _join(
        split_bit, addr_bit(entry_key, split_bit), leaf_hash(entry_key, new_commit), subtree
    )
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
    """One transition as a host logs it. The first five fields are opaque to the host; a
    NamedTuple, so indexing and slicing the old tuple keeps working."""

    from_counter: int
    from_root: Optional[bytes]
    to_counter: int
    to_root: Optional[bytes]
    auth_commit: bytes
    operation: str


class TransitionLog:
    """What a host keeps so other devices can walk the steps they missed.

    The operation (COMMIT/REVERT) is RECORDED: deriving it needs K_auth, which the host never has.
    `wm_sigs` maps a counter to the `wm_sig` of the transition that reached it, for the WM.
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
        """The predecessors of a state, walking back from it. The newest match wins: after a
        demotion a counter can be reached twice, and the later edge is the live history."""
        out: list = []
        state = _state(to_counter, to_root)
        while len(out) < limit:
            for link in reversed(self.links):
                if _state(link[2], link[3]) == state:
                    out.append(link)
                    state = _state(link[0], link[1])
                    break
            else:
                break
        return out

    def fork_point(self, a: tuple, b: tuple) -> Optional[int]:
        """The last counter two `(counter, root)` states share, walking both back; None if never.
        What a host passes as `WardRejoin.fork_counter` (the device checks it)."""
        ends = [_state(a[0], a[1]), _state(b[0], b[1])]
        while ends[0] != ends[1]:
            later = 0 if ends[0][0] >= ends[1][0] else 1
            prev = self.links_ending_at(*ends[later], limit=1)
            if not prev:
                return None
            ends[later] = _state(prev[0][0], prev[0][1])
        return ends[0][0]


# --- store: the tree ---------------------------------------------------------------------------


class WardTrie(TransitionLog):
    """A host's replica: entry_key -> leaf, the canonical root, proofs, and its transition log.

    The tree is cached until `set`/`remove`; `rebuild_root()` is the uncached oracle tests compare
    against. `root()` is None for an empty tree (the wire's "absent"); `root_or_empty()` is the
    preimage form.
    """

    def __init__(self) -> None:
        super().__init__()
        self._leaves: dict[bytes, bytes] = {}  # entry_key -> leaf hash
        self._commits: dict[bytes, bytes] = {}  # entry_key -> commit
        self.blobs: dict[bytes, object] = {}  # entry_key -> the Leaf the device built
        self._tree = None
        # roots repeat, so a state is (counter, root)
        self.counter = 0
        self.timestamp = 0

    # --- leaves ---

    def set(self, entry_key: bytes, leaf: object) -> None:
        """Store the leaf the device built. Only its sealed content is committed; the sealed
        identity is kept beside it."""
        commit = value_digest(leaf.content)
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
        """A copy with `staged` (entry_key, commit) leaves applied and no log: what a batched flush
        is served from, since the device proves against its running root."""
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
        return self._hash(self._root_node()) if self._leaves else None

    def root_or_empty(self) -> bytes:
        """The root in preimage form: EMPTY_ROOT for the empty tree."""
        root = self.root()
        return EMPTY_ROOT if root is None else root

    def rebuild_root(self) -> Optional[bytes]:
        """The root recomputed from scratch, ignoring the cache: the oracle `root()` is held to."""
        return self._hash(self._build(sorted(self._leaves), 0)) if self._leaves else None

    # --- proofs ---

    def _proof(self, node: tuple, target: bytes, out: list) -> bytes:
        if node[0] == "leaf":
            return self._leaves[node[1]]
        _, bit, left, right = node
        side = addr_bit(target, bit)
        here = self._proof(right if side else left, target, out)
        sibling = self._hash(left if side else right)
        out.append(proof_elem(bit, sibling))
        return _join(bit, side, here, sibling)

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
        The witness is the leaf a lookup for `entry_key` lands on."""
        if not self._leaves:
            return [], None, None
        node = self._root_node()
        while node[0] == "branch":
            node = node[2] if addr_bit(entry_key, node[1]) == 0 else node[3]
        witness = node[1]
        return self.membership_proof(witness), witness, self._commits[witness]
