"""The WARD Merkle trie: proof verification.

A path-compressed binary trie keyed by the 32-byte entry_key, so 256 levels at most:

    leaf     = sha256(0x00 || entry_key || commit)          -- see leaf.py
    internal = sha256(0x01 || u16be(split_bit) || u16be(skiplen) || left || right)

Children are POSITIONAL -- left is the 0 branch, right is the 1 branch, never sorted.
`split_bit` is the bit this node branches on; `skiplen` is how many bits were compressed
away between this node and its parent.

A proof is a list of 36-byte elements in LEAF-TO-ROOT order:

    u16be(split_bit) || u16be(skiplen) || sibling(32B)

This module VERIFIES; it never builds a trie. The host builds and serves proofs, and the
device only ever checks them against a root it already trusts. A proof verified against a
root the host also supplied proves nothing, so callers must pass a root of their own.

Byte-for-byte identical to the reference implementation and to @trezor/ward; the shared
conformance vectors are pinned in `core/tests/test_apps.ward.py`.

WHY split_bit AND skiplen ARE IN THE HASH -- this is the whole security of the thing.
An earlier version hashed only `0x01 || left || right` and put a 1-byte bit index in the
proof element. The bit position was therefore NOT committed to by the node hash, so a
host could relabel which bit each hop claimed to test while the hash chain still folded
to the same root. That defeats non-membership: absence is proved by exhibiting a witness
leaf that occupies the target's path, and "occupies the path" is judged by comparing bits
at the positions the proof claims. Free choice of those labels lets a host manufacture a
witness relationship and prove a key absent that is actually present. Binding split_bit
and skiplen into the preimage, plus the structural check below, closes it.

WHAT THIS STILL CANNOT CHECK. A canonical trie also requires that every internal node
has two non-empty children and that every skiplen is maximal for its subtree; otherwise
one key set admits several valid roots, because a host could pad depth or leave
single-child chains. Neither is decidable from a single proof -- the verifier sees only
one root-to-leaf path and cannot know what the sibling subtrees contain -- so what is
enforced here is the arithmetic consistency of the path, not canonicity of the tree.

That gap is a liveness problem, not an integrity one: proofs against a non-canonical root
still verify soundly, but a party that later rebuilds the tree canonically computes a
different root and rejects it, which is fail-closed and recoverable by rollback. The real
mitigation is a strictly specified construction plus conformance tests, which is why the
shared vectors in the tests matter more here than usual.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .leaf import Part

PROOF_ELEM_LEN = 36
_MAX_BITS = 256


def addr_bit(entry_key: bytes, bit: int) -> int:
    """Bit `bit` of the path, MSB-first: bit 0 is the top bit of byte 0."""
    return (entry_key[bit // 8] >> (7 - (bit % 8))) & 1


def internal_hash(split_bit: int, skiplen: int, left: bytes, right: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(
        b"\x01"
        + split_bit.to_bytes(2, "big")
        + skiplen.to_bytes(2, "big")
        + left
        + right
    ).digest()


def _parse_proof_elem(elem: bytes) -> "tuple[int, int, bytes]":
    from trezor.wire import DataError

    if len(elem) != PROOF_ELEM_LEN:
        raise DataError("WARD: invalid proof element length")
    return (
        int.from_bytes(elem[0:2], "big"),
        int.from_bytes(elem[2:4], "big"),
        bytes(elem[4:]),
    )


def validate_proof_shape(proof: "list[bytes]") -> "list[tuple[int, int, bytes]]":
    """Check the proof describes a well-formed root-to-leaf path, and return its steps.

    Walking ROOT to leaf (i.e. the proof reversed), the split bits must strictly increase
    and each skiplen must exactly account for the bits jumped over since the parent. A
    proof that is reordered, truncated and relabelled, or has its bit claims shifted
    fails here before a single hash is computed.

    This also bounds the work: split_bit strictly increases and stays below 256, so no
    valid proof exceeds 256 elements however many the host sends.
    """
    from trezor.wire import DataError

    steps = []
    start_bit = 0
    for elem in reversed(proof):
        split_bit, skiplen, sibling = _parse_proof_elem(elem)
        if split_bit >= _MAX_BITS:
            raise DataError("WARD: proof split_bit out of range")
        if split_bit < start_bit or skiplen != split_bit - start_bit:
            raise DataError("WARD: proof skiplen inconsistent with branch position")
        steps.append((split_bit, skiplen, sibling))
        start_bit = split_bit + 1
    return steps


def reconstruct(start_hash: bytes, proof: "list[bytes]", entry_key: bytes) -> bytes:
    """Fold a proof from a leaf up to a candidate root.

    `entry_key` is the path of the leaf the walk STARTS from -- for a non-membership
    proof that is the witness's path, not the absent key's.
    """
    validate_proof_shape(proof)

    node = start_hash
    for elem in proof:
        split_bit, skiplen, sibling = _parse_proof_elem(elem)
        if addr_bit(entry_key, split_bit) == 0:
            node = internal_hash(split_bit, skiplen, node, sibling)
        else:
            node = internal_hash(split_bit, skiplen, sibling, node)
    return node


def verify_membership(
    entry_key: bytes,
    key_type: str,
    id_part: "Part | None",
    val_part: "Part | None",
    proof: "list[bytes]",
    expected_root: bytes,
) -> bool:
    """Is this leaf in the tree with this root?

    Needs no key: the leaf hash is a commitment over the ENCODED parts, so the device
    checks membership without opening anything -- and a host with no keys at all can
    still serve the proof.

    Returns False on a proof that is well-formed but wrong; raises DataError on one that
    is malformed, since that is a protocol violation rather than a failed claim.
    """
    from .leaf import leaf_hash

    node = leaf_hash(entry_key, key_type, id_part, val_part)
    return reconstruct(node, proof, entry_key) == expected_root


def verify_nonmembership(
    entry_key: bytes,
    witness_entry_key: bytes,
    witness_commit: bytes,
    proof: "list[bytes]",
    expected_root: bytes,
) -> bool:
    """Is this path definitely EMPTY in the tree with this root?

    A binary trie has no "absent" node to point at, so absence is shown by exhibiting the
    leaf that already occupies the path the target would take. Three things must hold,
    and dropping any one of them makes the proof forgeable:

      1. the witness is a different key -- otherwise it proves presence, not absence;
      2. the witness is really in the tree, i.e. its leaf folds up to `expected_root`;
      3. the witness shares the target's path: the two agree at EVERY bit the proof
         branches on. Since the shape check has already forced those branch points to be
         strictly increasing with every skipped bit accounted for, agreeing at them is
         agreeing on the whole prefix down to where the paths part.

    Given all three, a leaf at the target's own path cannot exist: the lookup for it
    would descend exactly the branches proved here and arrive at the witness.

    The witness travels as two hashes -- its path and its commitment -- so serving an
    absence proof reveals nothing about the witness's identifier or value.
    """
    if witness_entry_key == entry_key:
        return False

    steps = validate_proof_shape(proof)
    for split_bit, _skiplen, _sibling in steps:
        if addr_bit(entry_key, split_bit) != addr_bit(witness_entry_key, split_bit):
            return False

    from .leaf import leaf_hash_of

    witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
    return reconstruct(witness_leaf, proof, witness_entry_key) == expected_root
