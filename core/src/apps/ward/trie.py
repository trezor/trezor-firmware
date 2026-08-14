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
    sibling_node: "tuple[int, bytes, bytes] | None" = None,
    sibling_leaf: "tuple[bytes, bytes] | None" = None,
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

    A DELETE must identify the collapsing sibling, as exactly one of `sibling_node`
    (split_bit, left, right) for a branch or `sibling_leaf` (entry_key, commit) for a leaf
    -- see below for why, and why neither may be inferred from the other's absence.
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

        for split_bit, _skiplen, _sibling in validate_proof_shape(proof):
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
        # Splicing there re-parents the branch immediately below, whose hash commits to a
        # skiplen measured from its old parent. Unlike the delete case the device can fix
        # this itself: that node is ON the path it is folding, so it holds both children
        # and simply re-folds it at the new depth.
        below = []
        idx = 0
        while idx < len(proof):
            sb, _sk, _sib = _parse_proof_elem(proof[idx])
            if sb <= split_bit:
                break
            below.append(proof[idx])
            idx += 1

        node = witness_leaf
        for i, elem in enumerate(below):
            sb, sk, sib = _parse_proof_elem(elem)
            if i == len(below) - 1:
                # the top of the spliced-off subtree: re-parented under the new branch
                sk = sb - (split_bit + 1)
            if addr_bit(witness_entry_key, sb) == 0:
                node = internal_hash(sb, sk, node, sib)
            else:
                node = internal_hash(sb, sk, sib, node)

        parent_split = _parse_proof_elem(proof[idx])[0] if idx < len(proof) else -1
        new_leaf_h = _leaf_of(entry_key, new_leaf)
        skiplen = split_bit - (parent_split + 1)
        if addr_bit(entry_key, split_bit) == 0:
            branch = internal_hash(split_bit, skiplen, new_leaf_h, node)
        else:
            branch = internal_hash(split_bit, skiplen, node, new_leaf_h)

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

    # Deleting collapses the branch above, and the sibling takes its place. That REPARENTS
    # the sibling, and a node's hash commits to its own skiplen, which is measured from
    # its parent -- so a BRANCH sibling's hash is stale the moment it moves, while a LEAF
    # has no skiplen and promotes exactly.
    #
    # The proof carries only the sibling's HASH, which does not say which of the two it is.
    # So the host must say, and PROVE it. Both forms are checked against that committed
    # hash, so neither can name a node the tree does not hold.
    #
    # Supplying neither is refused, and that refusal is the whole point of this shape. An
    # earlier revision let a leaf sibling be signalled by OMISSION -- and the device cannot
    # verify an omission. A host that withheld the decomposition for a branch got its root
    # promoted with a stale skiplen: a valid hash of a NON-CANONICAL tree over the same
    # leaves. No entry is forged or altered by that (the seal and the keyed path are
    # untouched), but every later proof from an honest, canonically-computing host
    # reconstructs to a different root and is refused, so the wallet is stuck.
    split_bit, skiplen, sibling = _parse_proof_elem(proof[0])
    if sibling_node is not None and sibling_leaf is not None:
        raise DataError("WARD: sibling is either a branch or a leaf, not both")

    if sibling_node is not None:
        sib_split, left, right = sibling_node
        if sib_split <= split_bit or sib_split >= _MAX_BITS:
            raise DataError(
                "WARD: sibling split_bit is not below the collapsing branch"
            )
        if (
            internal_hash(sib_split, sib_split - (split_bit + 1), left, right)
            != sibling
        ):
            raise DataError("WARD: sibling decomposition does not match the proof")
        # its parent moves up by the collapsed branch, so it absorbs that branch's own
        # skiplen plus the level itself
        sibling = internal_hash(
            sib_split, sib_split - (split_bit + 1) + skiplen + 1, left, right
        )
    elif sibling_leaf is not None:
        sib_key, sib_commit = sibling_leaf
        # Recomputing the leaf hash is what turns "it is a leaf" from a claim into a fact:
        # leaf and internal nodes are domain-separated (0x00 / 0x01), so a preimage that
        # reproduces the committed hash under the LEAF tag could not have been a branch.
        # The hash then promotes unchanged, which is correct precisely because it is one.
        if leaf_hash_of(sib_key, sib_commit) != sibling:
            raise DataError("WARD: sibling leaf does not match the proof")
    else:
        raise DataError("WARD: delete must identify the sibling")

    return reconstruct(sibling, proof[1:], entry_key)
