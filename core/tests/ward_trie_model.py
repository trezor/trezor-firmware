"""A canonical WARD trie, rebuilt from scratch. The reference the deriver is checked against.

This is the spec of `docs/core/misc/ward-trie.md` transcribed into code, and it is
deliberately the SLOW, OBVIOUS implementation: every query rebuilds the whole tree from the
sorted key set, there is no incremental update path and no cached state. That is the point.
`apps.ward.trie.compute_new_root` derives each new root from the previous one plus a proof,
which is fast and O(1) in the device's memory but can only be checked against something that
computes the same answer a different way.

WHY A SECOND MODEL EXISTS. `tests/ward_trie.py` is the host-side twin, used by the device
tests to serve proofs. Reusing it here would make the differential test circular in the one
place it must not be: if the model and the thing under test share code, they agree by
construction. Two independent rebuilders agreeing with the deriver is the actual property.
This one is written from the spec rather than ported from that one, and it runs in
MicroPython so the test can import the real firmware modules with no stubs.

EVERY trie bug found in this subsystem so far has been a canonicalisation disagreement
between a deriver and a rebuilder -- two in the reference implementation (delete
re-parenting a branch sibling, insert refusing a compressed-run splice) and one here (a
sibling's KIND inferred from an omission). None of them is detectable from inside the
device, which never rebuilds. Hence this file.
"""

from trezor.crypto.hashlib import sha256

# sha256(0x03): the root of the empty tree. Domain-separated from the leaf (0x00), internal
# (0x01) and commit (0x02) tags, so no real root can take this value.
EMPTY_ROOT = sha256(b"\x03").digest()

_MAX_BITS = 256


def addr_bit(entry_key: bytes, bit: int) -> int:
    """MSB-first: bit 0 is the top bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def leaf_hash(entry_key: bytes, commit: bytes) -> bytes:
    return sha256(b"\x00" + entry_key + commit).digest()


def internal_hash(split_bit: int, skiplen: int, left: bytes, right: bytes) -> bytes:
    return sha256(
        b"\x01"
        + split_bit.to_bytes(2, "big")
        + skiplen.to_bytes(2, "big")
        + left
        + right
    ).digest()


def proof_elem(split_bit: int, skiplen: int, sibling: bytes) -> bytes:
    return split_bit.to_bytes(2, "big") + skiplen.to_bytes(2, "big") + sibling


class CanonicalTrie:
    """entry_key -> commit, with the canonical root and proofs recomputed on every call.

    Nodes are tuples, built fresh each time:
        ("leaf", entry_key)
        ("branch", split_bit, skiplen, left, right)
    """

    def __init__(self) -> None:
        self.commits = {}

    # --- store ---

    def set(self, entry_key: bytes, commit: bytes) -> None:
        self.commits[entry_key] = commit

    def remove(self, entry_key: bytes) -> None:
        self.commits.pop(entry_key, None)

    def __contains__(self, entry_key: bytes) -> bool:
        return entry_key in self.commits

    def __len__(self) -> int:
        return len(self.commits)

    # --- structure ---

    def _build(self, keys, start_bit: int):
        """The canonical subtree over `keys`, whose parent branched at `start_bit - 1`."""
        if len(keys) == 1:
            return ("leaf", keys[0])

        # the lowest bit at or below start_bit on which this key set splits
        split = start_bit
        while split < _MAX_BITS:
            first = addr_bit(keys[0], split)
            if any(addr_bit(k, split) != first for k in keys[1:]):
                break
            split += 1
        if split >= _MAX_BITS:
            raise ValueError("duplicate entry_key")

        left = [k for k in keys if addr_bit(k, split) == 0]
        right = [k for k in keys if addr_bit(k, split) == 1]
        # skiplen counts the bits jumped over since the parent branched: this is the
        # quantity that goes stale whenever a node is re-parented, and the reason a delete
        # cannot simply promote a branch sibling's hash.
        return (
            "branch",
            split,
            split - start_bit,
            self._build(left, split + 1),
            self._build(right, split + 1),
        )

    def _tree(self):
        return self._build(sorted(self.commits), 0)

    def _hash(self, node) -> bytes:
        if node[0] == "leaf":
            return leaf_hash(node[1], self.commits[node[1]])
        return internal_hash(node[1], node[2], self._hash(node[3]), self._hash(node[4]))

    def root(self) -> bytes:
        """The canonical root. An empty tree is EMPTY_ROOT, never None."""
        if not self.commits:
            return EMPTY_ROOT
        return self._hash(self._tree())

    # --- proofs ---

    def _descend(self, entry_key: bytes):
        """Follow `entry_key`'s bits to whatever leaf they reach.

        Returns (leaf_node, path), where `path` is root-to-leaf and each entry is
        (split_bit, skiplen, sibling_node). Used for both membership (the leaf found IS the
        key) and non-membership (it is the witness occupying that path).
        """
        node = self._tree()
        path = []
        while node[0] == "branch":
            _t, split, skiplen, left, right = node
            if addr_bit(entry_key, split) == 0:
                path.append((split, skiplen, right))
                node = left
            else:
                path.append((split, skiplen, left))
                node = right
        return node, path

    def _proof_from_path(self, path):
        """Path elements, leaf-to-root, in wire form."""
        return [
            proof_elem(split, skiplen, self._hash(sib))
            for split, skiplen, sib in reversed(path)
        ]

    def membership_proof(self, entry_key: bytes):
        assert entry_key in self.commits
        leaf, path = self._descend(entry_key)
        assert leaf[1] == entry_key
        return self._proof_from_path(path)

    def nonmembership_witness(self, entry_key: bytes):
        """(proof, witness_entry_key, witness_commit) for a path that holds nothing.

        A binary trie has no "absent" node to point at, so absence is shown by exhibiting
        the leaf the lookup would arrive at instead. On an empty tree there is nothing to
        exhibit, and none is needed: (empty proof, None, None).
        """
        assert entry_key not in self.commits
        if not self.commits:
            return [], None, None
        leaf, path = self._descend(entry_key)
        wkey = leaf[1]
        return self._proof_from_path(path), wkey, self.commits[wkey]

    def sibling_witness(self, entry_key: bytes):
        """What a DELETE of `entry_key` must present, or None if it is the last leaf.

        ("branch", split_bit, left_hash, right_hash) when the promoted sibling is a branch:
        it moves up a level, and its hash commits to a skiplen measured from its old parent,
        so the device has to re-derive it and can only do that from the pieces.

        ("leaf", entry_key, commit) when the sibling is a leaf: it promotes unchanged. The
        device is still not allowed to ASSUME that from a missing decomposition -- it cannot
        verify an omission -- so it recomputes the leaf hash and matches it.
        """
        assert entry_key in self.commits
        if len(self.commits) == 1:
            return None
        _leaf, path = self._descend(entry_key)
        sib = path[-1][2]  # the sibling under the branch directly above the leaf
        if sib[0] == "leaf":
            return ("leaf", sib[1], self.commits[sib[1]])
        return ("branch", sib[1], self._hash(sib[3]), self._hash(sib[4]))
