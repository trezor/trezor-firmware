"""The WARD Merkle trie: proof verification.

A path-compressed binary trie keyed by the 32-byte entry_key, so 256 levels at most:

    leaf     = sha256(0x00 || entry_key || commit)          -- see leaf.py
    internal = sha256(0x01 || u16be(split_bit) || left || right)

Children are POSITIONAL -- left is the 0 branch, right is the 1 branch, never sorted.
`split_bit` is the bit this node branches on.

A proof is a list of 34-byte elements in LEAF-TO-ROOT order:

    u16be(split_bit) || sibling(32B)

This module VERIFIES; it never builds a trie. The host builds and serves proofs, and the
device only ever checks them against a root it already trusts. A proof verified against a
root the host also supplied proves nothing, so callers must pass a root of their own.

Byte-for-byte identical to the reference implementation and to @trezor/ward; the shared
conformance vectors are pinned in `core/tests/test_apps.ward.py`.

WHY split_bit IS IN THE HASH -- this is the whole security of the thing. An earlier
version hashed only `0x01 || left || right` and put a bit index in the proof element. The
bit position was therefore NOT committed to by the node hash, so a host could relabel
which bit each hop claimed to test while the hash chain still folded to the same root.
That defeats non-membership: absence is proved by exhibiting a witness leaf that occupies
the target's path, and "occupies the path" is judged by comparing bits at the positions
the proof claims. Free choice of those labels lets a host manufacture a witness
relationship and prove a key absent that is actually present. Binding split_bit into the
preimage, plus the structural check below, closes it.

AND WHY skiplen IS NOT. It used to be, alongside split_bit -- the two were introduced in
one change, so the fix was credited to both. Only split_bit was load-bearing. skiplen is a
FUNCTION of already-committed data: walking a proof root-to-leaf it is exactly
split_bit - (previous split_bit + 1), which `validate_proof_shape` recomputed and compared
rather than verifying against anything independent. Committing to a value the verifier
derives binds nothing.

Removing it is not merely tidier: it makes a node's hash INDEPENDENT OF ITS DEPTH, so a
subtree that re-parents keeps its hash. That is what makes delete trivial -- the collapsing
sibling promotes unchanged whether it is a leaf or a branch -- and it is what removed the
sibling-kind witness the wire used to carry. All three trie bugs this subsystem has had
were artifacts of the depth binding: a branch sibling promoted unchanged (non-canonical
then, correct now), an insert refusing to splice above an existing branch, and a sibling
whose kind had to be proved because the two kinds re-parented differently.

WHAT THIS STILL CANNOT CHECK. A canonical trie also requires that every internal node has
two non-empty children and that each branches at the FIRST bit on which its keys diverge;
otherwise one key set admits several valid roots. Neither is decidable from a single proof
-- the verifier sees only one root-to-leaf path and cannot know what the sibling subtrees
contain -- so what is enforced here is the consistency of the path, not canonicity of the
tree.

That gap is a liveness problem, not an integrity one: proofs against a non-canonical root
still verify soundly, but a party that later rebuilds the tree canonically computes a
different root and rejects it, which is fail-closed and recoverable by rollback. The real
mitigation is a strictly specified construction plus conformance tests, which is why the
shared vectors in the tests matter more here than usual.
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
    """Check the proof describes a well-formed root-to-leaf path, and return its steps.

    Walking ROOT to leaf (i.e. the proof reversed), the split bits must strictly increase.
    A proof that is reordered or has its bit claims shifted fails here before a single hash
    is computed. This used to also check that each skiplen accounted for the bits jumped
    over since the parent; that value is no longer carried, being derivable from exactly
    these split bits.

    This also bounds the work: split_bit strictly increases and stays below 256, so no
    valid proof exceeds 256 elements however many the host sends.
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
    """Fold a proof from a leaf up to a candidate root.

    `entry_key` is the path of the leaf the walk STARTS from -- for a non-membership
    proof that is the witness's path, not the absent key's.
    """
    validate_proof_shape(proof)

    node = start_hash
    for elem in proof:
        split_bit, sibling = _parse_proof_elem(elem)
        if addr_bit(entry_key, split_bit) == 0:
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

      0. every operand is exactly 32 bytes -- see the comment below, this one is load-bearing;
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
    # Lengths FIRST. "differs from the target" and "agrees at every branch bit" are both
    # satisfied by a witness key that is the target with extra bytes glued on -- and since
    # the leaf preimage concatenates key and commit with no boundary marker, K || C[0] with
    # commit C[1:] hashes to the target's own leaf. A host could then pass the target's
    # MEMBERSHIP proof off as proof of absence. `leaf.leaf_hash_of` refuses that too; this
    # rejects it before the comparisons below, which would otherwise pass and read as though
    # the witness relationship were real.
    if (
        len(entry_key) != 32
        or len(witness_entry_key) != 32
        or len(witness_commit) != 32
    ):
        return False

    if witness_entry_key == entry_key:
        return False

    steps = validate_proof_shape(proof)
    for split_bit, _sibling in steps:
        if addr_bit(entry_key, split_bit) != addr_bit(witness_entry_key, split_bit):
            return False

    from .leaf import leaf_hash_of

    witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
    return reconstruct(witness_leaf, proof, witness_entry_key) == expected_root


def _leaf_of(entry_key: bytes, leaf) -> bytes:
    from .leaf import leaf_hash

    return leaf_hash(entry_key, leaf[0], leaf[1], leaf[2])


def compute_new_root(
    entry_key: bytes,
    old_leaf,
    new_leaf,
    proof: "list[bytes]",
    stored_root: bytes | None,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> bytes:
    """Verify the CURRENT state, then derive the root that replaces it.

    `old_leaf` / `new_leaf` are (key_type, id_part, val_part) triples the device built, or
    None: old_leaf=None inserts, new_leaf=None deletes. Always returns a root -- a tree
    emptied by a delete is EMPTY_ROOT, never None, so that "the tree is empty" can never be
    confused with "this device has no root and therefore checks nothing". Raises rather
    than returning a bool: a write must abort, not proceed on a false.

    The point of this function is that the device never takes the host's word for the
    state it is replacing. In every branch but the very first insert, the host must PROVE
    the current leaf (or the current absence) against the root the device already holds,
    before the device will compute anything from it. A host cannot walk the device through
    a fabricated present to land it on a chosen future.

    A DELETE needs nothing beyond the proof: the collapsing sibling promotes unchanged.
    """
    from trezor.wire import DataError

    from .attest import EMPTY_ROOT
    from .leaf import leaf_hash_of

    # An empty tree has a root like any other state; what it does not have is anything to
    # prove a membership against. `stored_root is None` means something entirely different
    # -- this device has never written -- and the two must not be collapsed.
    empty = stored_root is None or stored_root == EMPTY_ROOT

    inserting = old_leaf is None
    deleting = new_leaf is None
    if inserting and deleting:
        raise DataError("WARD: nothing to write")

    if inserting:
        if not proof and witness_entry_key is None:
            # The first entry of an empty tree: there is no state to prove, so the
            # device's OWN record that the tree is empty is the only authority accepted
            # here. That covers both a device that has never written and one whose last
            # entry was deleted.
            if not empty:
                raise DataError("WARD: tree is not empty; a witness is required")
            return _leaf_of(entry_key, new_leaf)

        if witness_entry_key is None or witness_commit is None:
            raise DataError("WARD: insert needs a non-membership witness")
        if witness_entry_key == entry_key:
            raise DataError("WARD: witness must differ from entry_key")

        for split_bit, _sibling in validate_proof_shape(proof):
            if addr_bit(entry_key, split_bit) != addr_bit(witness_entry_key, split_bit):
                raise DataError("WARD: witness does not occupy the target's path")

        witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
        if reconstruct(witness_leaf, proof, witness_entry_key) != stored_root:
            raise DataError("WARD: witness is not in the tree")

        # Where the two paths part is computed HERE, never taken from the host: it decides
        # where the new leaf is spliced in, so a host-chosen value would let it graft the
        # entry somewhere structurally inconsistent with the rest of the tree.
        split_bit = -1
        for b in range(_MAX_BITS):
            if addr_bit(entry_key, b) != addr_bit(witness_entry_key, b):
                split_bit = b
                break
        if split_bit < 0:
            raise DataError("WARD: entry_key and witness are equal")

        # The new branch goes at `split_bit`, which is NOT necessarily below every branch
        # on the witness's path. Path compression means the two keys are only compared at
        # the bits the tree actually branches on, so they can agree at all of those and
        # still part inside a compressed run -- i.e. ABOVE an existing branch. That is the
        # ordinary case for a random key, not a corner one.
        #
        # Splicing there re-parents the branch immediately below, and that used to need
        # fixing up: the node's hash committed to a depth that had just changed. It no
        # longer does, so the spliced-off subtree folds unchanged.
        below = []
        idx = 0
        while idx < len(proof):
            sb, _sib = _parse_proof_elem(proof[idx])
            if sb <= split_bit:
                break
            below.append(proof[idx])
            idx += 1

        node = witness_leaf
        for elem in below:
            sb, sib = _parse_proof_elem(elem)
            if addr_bit(witness_entry_key, sb) == 0:
                node = internal_hash(sb, node, sib)
            else:
                node = internal_hash(sb, sib, node)

        new_leaf_h = _leaf_of(entry_key, new_leaf)
        if addr_bit(entry_key, split_bit) == 0:
            branch = internal_hash(split_bit, new_leaf_h, node)
        else:
            branch = internal_hash(split_bit, node, new_leaf_h)

        # above the splice the two keys agree, so folding by either path is the same
        return reconstruct(branch, proof[idx:], witness_entry_key)

    # Both DELETE and UPDATE must first prove the leaf they claim to be replacing. An
    # empty tree holds no leaf to replace, so there is nothing either could be proving.
    if empty:
        raise DataError("WARD: no trusted root")
    current = _leaf_of(entry_key, old_leaf)
    if reconstruct(current, proof, entry_key) != stored_root:
        raise DataError("WARD: current entry does not match the trusted root")

    if not deleting:
        return reconstruct(_leaf_of(entry_key, new_leaf), proof, entry_key)

    if not proof:
        return EMPTY_ROOT  # the last leaf is gone; the tree is empty, and says so

    # Deleting collapses the branch above, and the sibling takes its place -- unchanged,
    # whatever it is. A node's hash no longer depends on its depth, so a re-parented subtree
    # keeps the hash the proof already committed to, and a leaf and a branch behave
    # identically here.
    #
    # This used to be the hardest corner in the module. The hash bound a skiplen measured
    # from the old parent, so a branch sibling's hash went stale the instant it moved while a
    # leaf's did not -- which meant the device had to be TOLD which kind it was, and could
    # not verify the answer. Two wire fields, a decomposition check and a refusal existed for
    # that, and all of it was an artifact of committing to depth.
    split_bit, sibling = _parse_proof_elem(proof[0])
    return reconstruct(sibling, proof[1:], entry_key)
