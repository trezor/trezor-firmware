"""The WARD Merkle trie: proof verification.

A path-compressed binary trie keyed by the 32-byte entry_key:

    leaf     = sha256(0x00 || entry_key || commit)          -- see leaf.py
    internal = sha256(0x01 || u16be(split_bit) || left || right)

Children are positional (left = 0 branch). A proof is a list of 34-byte elements,
`u16be(split_bit) || sibling(32B)`, in LEAF-TO-ROOT order. The device only verifies proofs
against a root it already trusts; conformance vectors are pinned in `core/tests/test_apps.ward.py`.

split_bit is IN THE HASH, which is what stops a host relabelling the bits a proof claims to
branch on and forging non-membership. Node hashes do not depend on depth, so a re-parented
subtree keeps its hash.

Canonicity (two non-empty children, branching at the first divergent bit) is not decidable
from one path; a non-canonical root still verifies soundly and fails closed on rebuild. A root
adopted through `rollback` was not derived here, so a genuine old leaf on the wrong side of a
branch proves absent until a later delete promotes it back.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .leaf import Part

PROOF_ELEM_LEN = 34
_MAX_BITS = 256


def addr_bit(entry_key: bytes, bit: int) -> int:
    """Bit `bit` of the path, MSB-first: bit 0 is the top bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def internal_hash(split_bit: int, left: bytes, right: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(b"\x01" + split_bit.to_bytes(2, "big") + left + right).digest()


def _parse_proof_elem(elem: bytes) -> "tuple[int, bytes]":
    from trezor.wire import DataError

    if len(elem) != PROOF_ELEM_LEN:
        raise DataError("WARD: invalid proof element length")
    return int.from_bytes(elem[0:2], "big"), bytes(elem[2:])


def validate_proof_shape(proof: "list[bytes]") -> "list[tuple[int, bytes]]":
    """Root-to-leaf steps of a well-formed proof: split bits strictly increasing, below 256.

    Also bounds the work to 256 elements however many the host sends.
    """
    from trezor.wire import DataError

    steps = []
    start_bit = 0
    for elem in reversed(proof):
        split_bit, sibling = _parse_proof_elem(elem)
        if split_bit >= _MAX_BITS:
            raise DataError("WARD: proof split_bit out of range")
        if split_bit < start_bit:
            raise DataError("WARD: proof split bits are not strictly increasing")
        steps.append((split_bit, sibling))
        start_bit = split_bit + 1
    return steps


def reconstruct(start_hash: bytes, proof: "list[bytes]", entry_key: bytes) -> bytes:
    """Fold a proof from a leaf up to a candidate root; `entry_key` is the STARTING leaf's path."""
    from trezor.wire import DataError

    # A long key would route by its first 32 bytes while the leaf preimage has no boundary.
    if len(start_hash) != 32 or len(entry_key) != 32:
        raise DataError("WARD: reconstruct operands must be 32 bytes")

    return _fold(start_hash, reversed(validate_proof_shape(proof)), entry_key)


def _fold(node: bytes, steps, path: bytes) -> bytes:
    """Hash `node` up through leaf-to-root `(split_bit, sibling)` steps, sided by `path`."""
    for split_bit, sibling in steps:
        if addr_bit(path, split_bit) == 0:
            node = internal_hash(split_bit, node, sibling)
        else:
            node = internal_hash(split_bit, sibling, node)
    return node


def verify_membership(
    entry_key: bytes,
    key_type: str,
    id_part: "Part | None",
    val_part: "Part | None",
    proof: "list[bytes]",
    expected_root: bytes,
) -> bool:
    """Is this leaf in the tree with this root? False if wrong; DataError if malformed."""
    from .leaf import leaf_hash

    node = leaf_hash(entry_key, key_type, id_part, val_part)
    return reconstruct(node, proof, entry_key) == expected_root


def _absence_failure(
    entry_key: bytes,
    witness_entry_key: bytes,
    witness_commit: bytes,
    proof: "list[bytes]",
    expected_root: bytes | None,
) -> "str | None":
    """Why this witness does NOT prove `entry_key` absent under `expected_root`, or None.

    The one non-membership check, shared by reads and inserts.
    """
    # Widths FIRST, and raising: a witness key K || C[0] with commit C[1:] hashes to the
    # target's own leaf, which would pass a MEMBERSHIP proof off as absence.
    from trezor.wire import DataError

    if (
        len(entry_key) != 32
        or len(witness_entry_key) != 32
        or len(witness_commit) != 32
    ):
        raise DataError("WARD: witness operands must be 32 bytes")

    if witness_entry_key == entry_key:
        return "WARD: witness must differ from entry_key"

    for split_bit, _sibling in validate_proof_shape(proof):
        if addr_bit(entry_key, split_bit) != addr_bit(witness_entry_key, split_bit):
            return "WARD: witness does not occupy the target's path"

    from .leaf import leaf_hash_of

    witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
    if reconstruct(witness_leaf, proof, witness_entry_key) != expected_root:
        return "WARD: witness is not in the tree"
    return None


def verify_nonmembership(
    entry_key: bytes,
    witness_entry_key: bytes,
    witness_commit: bytes,
    proof: "list[bytes]",
    expected_root: bytes,
) -> bool:
    """Is this path EMPTY under this root? Shown by the witness leaf occupying its path.

    Requires: 32-byte operands (raises otherwise), a witness different from the target, in
    the tree, and agreeing with the target at every bit the proof branches on.
    """
    return (
        _absence_failure(
            entry_key, witness_entry_key, witness_commit, proof, expected_root
        )
        is None
    )


def _leaf_of(entry_key: bytes, leaf) -> bytes:
    from .leaf import leaf_hash

    return leaf_hash(entry_key, leaf[0], leaf[1], leaf[2])


def compute_new_root(
    entry_key: bytes,
    old_leaf,
    new_leaf,
    proof: "list[bytes]",
    stored_root: bytes,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> bytes:
    """Verify the CURRENT state against `stored_root`, then derive the root replacing it.

    `old_leaf`/`new_leaf` are (key_type, id_part, val_part) or None (None old = insert, None
    new = delete). Returns a root (EMPTY_ROOT when emptied, never None); raises on failure.
    Except for the first insert into an empty tree, the host must prove the current leaf or
    absence before anything is derived.
    """
    from trezor.wire import DataError

    from .attest import EMPTY_ROOT
    from .leaf import leaf_hash_of

    # None is "cannot verify", never empty: as empty it would allow a witness-less insert.
    if stored_root is None:
        raise DataError("WARD: no trusted root")
    empty = stored_root == EMPTY_ROOT

    inserting = old_leaf is None
    deleting = new_leaf is None
    if inserting and deleting:
        raise DataError("WARD: nothing to write")

    if inserting:
        if not proof and witness_entry_key is None:
            if not empty:
                raise DataError("WARD: tree is not empty; a witness is required")
            return _leaf_of(entry_key, new_leaf)

        if witness_entry_key is None or witness_commit is None:
            raise DataError("WARD: insert needs a non-membership witness")

        # Checked here, not left to the read path, which skips it for an emptied tree.
        failure = _absence_failure(
            entry_key, witness_entry_key, witness_commit, proof, stored_root
        )
        if failure is not None:
            raise DataError(failure)
        witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)

        # The splice point is computed here, never taken from the host.
        split_bit = -1
        for b in range(_MAX_BITS):
            if addr_bit(entry_key, b) != addr_bit(witness_entry_key, b):
                split_bit = b
                break
        if split_bit < 0:
            raise DataError("WARD: entry_key and witness are equal")

        # `split_bit` may fall ABOVE existing branches on the witness's path (inside a
        # compressed run); the subtree below folds unchanged.
        steps = [_parse_proof_elem(elem) for elem in proof]  # leaf-to-root
        idx = 0
        while idx < len(steps) and steps[idx][0] >= split_bit:
            if steps[idx][0] == split_bit:
                # Unreachable (the absence check rejects this); explicit by design.
                raise DataError("WARD: witness path already branches at the split bit")
            idx += 1
        node = _fold(witness_leaf, steps[:idx], witness_entry_key)

        new_leaf_h = _leaf_of(entry_key, new_leaf)
        if addr_bit(entry_key, split_bit) == 0:
            branch = internal_hash(split_bit, new_leaf_h, node)
        else:
            branch = internal_hash(split_bit, node, new_leaf_h)

        # above the splice the two keys agree, so folding by either path is the same
        return reconstruct(branch, proof[idx:], witness_entry_key)

    # DELETE and UPDATE must first prove the leaf they replace.
    if empty:
        raise DataError("WARD: the tree is empty; nothing to replace")
    current = _leaf_of(entry_key, old_leaf)
    if reconstruct(current, proof, entry_key) != stored_root:
        raise DataError("WARD: current entry does not match the trusted root")

    if not deleting:
        return reconstruct(_leaf_of(entry_key, new_leaf), proof, entry_key)

    if not proof:
        return EMPTY_ROOT  # the last leaf is gone; the tree is empty, and says so

    # The sibling replaces the collapsed branch unchanged, leaf or subtree alike.
    _split_bit, sibling = _parse_proof_elem(proof[0])
    return reconstruct(sibling, proof[1:], entry_key)
