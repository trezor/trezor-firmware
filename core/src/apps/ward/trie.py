"""The WARD Merkle trie: proof verification and root derivation.

The trie is `trezor_ward`'s authenticated crit-bit tree over the 32-byte entry_key,
verified in Rust (`trezorward.trie_*`):

    leaf   = sha256(0x00 || entry_key || commit)        commit = leaf.commit_of(...)
    branch = sha256(0x01 || split_bit || left || right)  split_bit: 1 byte
    empty  = sha256(0x02)

Children are POSITIONAL -- left is the 0 branch, right is the 1 branch. A proof on the
wire is a list of 33-byte steps in LEAF-TO-ROOT order, `split_bit || sibling`; the
leaf it starts from is never taken from the host as a digest when the device can
compute it: a membership proof starts at the leaf the device commits to from the two
parts it holds, a non-membership proof at the witness (entry_key, commit) the host
names. Here the two are put together as the Rust proof `key || commit || steps`.

This module never builds a trie and never derives a root from a proof it has not held
against a root it already trusts: every derived root comes from the Rust entry the
verification produced. A proof verified against a root the host also supplied proves
nothing, so callers must pass a root of their own.
"""

from trezor.crypto.hashlib import sha256
from trezorward import (
    trie_lookup,
    trie_remove,
    trie_replace_all,
    trie_set,
    trie_walk_done,
    trie_walk_next,
    trie_walk_next_len,
)

from .leaf import commit_of

PROOF_STEP_LEN = 33  # split_bit(1B) || sibling(32B)

# The root of the empty tree; callers hold `None` for it.
EMPTY_ROOT = sha256(b"\x02").digest()


def _root(root) -> bytes:
    return EMPTY_ROOT if root is None else root


def _proof(terminal_key: bytes, commit: bytes, steps: list) -> bytes:
    """The Rust proof `terminal_key || commit || steps`. Every operand has a fixed
    width: a key or a step of another length would shift the ones after it, so it is
    refused here rather than read as some other proof."""
    if len(terminal_key) != 32 or len(commit) != 32:
        raise ValueError("WARD: leaf operands must be 32 bytes")
    for step in steps:
        if len(step) != PROOF_STEP_LEN:
            raise ValueError("invalid proof element length")
    return terminal_key + commit + b"".join(steps)


def verify_proof(
    entry_key_: bytes,
    key_type: str,
    id_part,
    val_part,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Whether the leaf (key_type, id_part, val_part) is a member at entry_key under
    expected_root. A step of the wrong width raises ValueError; any proof that is
    refused otherwise is not valid."""
    p = _proof(entry_key_, commit_of(key_type, id_part, val_part), proof)
    try:
        return trie_lookup(expected_root, entry_key_, p) is not None
    except ValueError:
        return False


def verify_nonmembership(
    entry_key_: bytes,
    witness_entry_key: bytes,
    witness_commit: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Whether entry_key is NOT in the tree with expected_root.

    The witness leaf (witness_entry_key, witness_commit) is the leaf a lookup for
    entry_key ends at, named by its two hashes, which reveal nothing of its
    identifier or value. The proof starts there and must be entry_key's lookup path
    (`OffPath` otherwise) and fold to the root.

    The widths come first and RAISE: a witness key that is the target with bytes
    glued on would otherwise hash to the target's own leaf, so the target's own
    membership proof would pass as proof of its absence. A wrong-width operand is a
    malformed message, not a claim that failed, and the two must not read alike."""
    from trezor.wire import DataError

    if (
        len(entry_key_) != 32
        or len(witness_entry_key) != 32
        or len(witness_commit) != 32
    ):
        raise DataError("WARD: witness operands must be 32 bytes")
    if witness_entry_key == entry_key_:
        return False
    try:
        p = _proof(witness_entry_key, witness_commit, proof)
        return trie_lookup(expected_root, entry_key_, p) is None
    except ValueError:
        return False


def compute_new_root(
    entry_key_: bytes,
    old_leaf,
    new_leaf,
    proof: list,
    stored_root,
    witness_entry_key=None,
    witness_commit=None,
):
    """Verify the old state against stored_root, then compute the new root.
    `old_leaf`/`new_leaf` are (key_type, id_part, val_part) tuples the device
    produced, or None: old_leaf=None => INSERT, new_leaf=None => DELETE. Returns the
    new root (None if the tree becomes empty), or raises ValueError if the old-state
    proof does not verify. INSERT's witness neighbour may belong to another app, so
    it is supplied privacy-preservingly as (witness_entry_key, witness_commit)."""
    inserting = old_leaf is None
    deleting = new_leaf is None
    if inserting and deleting:
        raise ValueError("old_leaf and new_leaf cannot both be empty")

    if inserting:
        new_commit = commit_of(new_leaf[0], new_leaf[1], new_leaf[2])
        if len(proof) == 0 and witness_entry_key is None:
            # INIT: the tree was empty
            if stored_root is not None:
                raise ValueError("Tree is not empty; supply non-membership proof")
            return trie_set(EMPTY_ROOT, entry_key_, b"", new_commit, False)
        if witness_entry_key is None or witness_commit is None:
            raise ValueError("witness_entry_key/witness_commit required for INSERT")
        if (
            len(entry_key_) != 32
            or len(witness_entry_key) != 32
            or len(witness_commit) != 32
        ):
            raise ValueError("INSERT operands must be 32 bytes")
        if witness_entry_key == entry_key_:
            raise ValueError("witness_entry_key must differ from entry_key")
        # The witness is not entry_key, so the entry is vacant, and the Rust insert
        # refuses it otherwise. Where the new branch goes is computed there from the
        # two keys, never taken from the host.
        p = _proof(witness_entry_key, witness_commit, proof)
        return trie_set(_root(stored_root), entry_key_, p, new_commit, False)

    if stored_root is None:
        raise ValueError("No Merkle root stored on device")
    p = _proof(entry_key_, commit_of(old_leaf[0], old_leaf[1], old_leaf[2]), proof)

    if deleting:
        # The branch above collapses and its other child takes its place unchanged.
        root = trie_remove(stored_root, entry_key_, p)
        return None if root == EMPTY_ROOT else root

    # UPDATE
    new_commit = commit_of(new_leaf[0], new_leaf[1], new_leaf[2])
    return trie_set(stored_root, entry_key_, p, new_commit, True)


def compute_batch_root(stored_root, ops):
    """Apply a batch of leaf changes to `stored_root` and return the new root (`None`
    if the tree ends empty). Rejects a duplicate `entry_key` within the batch (§4.2).

    Each op is a 6-tuple `(entry_key, old_leaf, new_leaf, proof, witness_entry_key,
    witness_commit)` with the same semantics as `compute_new_root` (old_leaf=None =>
    INSERT, new_leaf=None => DELETE), and `proof` is the pre-state proof against
    `stored_root` (the single common base the host serves for the whole batch).

    - A single-op batch (n=1) is `compute_new_root`: INIT / INSERT / UPDATE / DELETE.
    - A multi-op batch supports **UPDATES only** (the trie shape is unchanged) and is
      one Rust call (`trie_replace_all`): the updates are made in turn on one root,
      each proof held against the root the ones before left, and the proofs still to
      come follow each update. Nothing here carries a root from one update to the
      next.

    Per-leaf counter monotonicity (`C_new > C_old`, §4.5/F12) is enforced by the
    caller (`perform_batch`), not here."""
    if not ops:
        raise ValueError("empty batch")
    seen = []
    for op in ops:
        ek = op[0]
        for prev in seen:
            if prev == ek:
                raise ValueError("duplicate entry_key in batch")
        seen.append(ek)

    if len(ops) == 1:
        op = ops[0]
        return compute_new_root(
            op[0],
            op[1],
            op[2],
            op[3],
            stored_root,
            witness_entry_key=op[4],
            witness_commit=op[5],
        )

    if stored_root is None:
        raise ValueError("multi-leaf update batch requires a non-empty tree")
    keys, proofs, commits = [], [], []
    for ek, old_leaf, new_leaf, proof, w_ek, _w_commit in ops:
        if old_leaf is None or new_leaf is None or w_ek is not None:
            raise ValueError(
                "multi-leaf batch supports UPDATES only; use single-leaf commits "
                "for insert/delete"
            )
        old_commit = commit_of(old_leaf[0], old_leaf[1], old_leaf[2])
        keys.append(ek)
        # written in place as the updates before it are made
        proofs.append(bytearray(_proof(ek, old_commit, proof)))
        commits.append(commit_of(new_leaf[0], new_leaf[1], new_leaf[2]))
    return trie_replace_all(stored_root, keys, proofs, commits)


class EntryWalk:
    """The entries of the tree with one trusted root, in entry_key order, one proof
    per entry (`trezor_ward`'s Walk), so the host can neither hide, repeat nor
    reorder one: an entry is accepted only if its proof holds against the root and it
    is the successor of the one before.

    The host sends each entry's leaf parts and its proof steps, either all of them or
    only those below the branch where it parts from the previous entry; the device
    completes the proof from the one it holds. The walk ends when the last entry
    accepted is the largest key, which the device reads off that entry's proof, so the
    host has no say in when the listing is complete."""

    def __init__(self, root) -> None:
        self.root = _root(root)
        self.current = None  # the current entry's full proof
        self.key = None  # the current entry's entry_key; None before the first

    def done(self) -> bool:
        return trie_walk_done(self.root, self.current)

    def next(self, entry_key_: bytes, commit: bytes, steps: list) -> None:
        """Accept the leaf (entry_key, commit) with `steps` as the next entry. Raises
        ValueError if it is not the next entry, or its proof does not hold."""
        p = _proof(entry_key_, commit, steps)
        buf = bytearray(trie_walk_next_len(self.root, self.current, p))
        self.key, _commit = trie_walk_next(self.root, self.current, p, buf)
        self.current = buf
