"""The WARD Merkle trie: proof verification and root derivation.

A path-compressed binary trie keyed by the 32-byte entry_key, so 256 levels at most:

    leaf     = sha256(0x00 || entry_key || commit)          -- see `leaf`
    internal = sha256(0x01 || u16be(split_bit) || left || right)

Children are POSITIONAL -- left is the 0 branch, right is the 1 branch, never sorted.
`split_bit` is the bit this node branches on.

A proof is a list of 34-byte elements in LEAF-TO-ROOT order:

    u16be(split_bit) || sibling(32B)

This module verifies proofs and derives the root that a write produces. It never builds
a trie: the host builds and serves proofs, and the device only ever checks them against
a root it already trusts. A proof verified against a root the host also supplied proves
nothing, so callers must pass a root of their own.

Split out of `service` so the one part of WARD that is pure, total and free of device
state can be read and tested as such: it takes bytes and returns bytes, holds no keys,
touches no storage, and shows no screens. `leaf` is the only WARD module it imports,
and only to hash a leaf.
"""

from typing import TYPE_CHECKING

# The ONE edge out of this module, and only to hash a leaf. Module level rather than
# lazy inside six functions: `leaf` imports nothing from here, so there is no cycle to
# break, and a proof fold should not pay an import lookup per call.
from .leaf import leaf_hash, leaf_hash_of

if TYPE_CHECKING:
    pass


def _sha256d(data: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


def addr_bit(entry_key_: bytes, bit: int) -> int:
    return (entry_key_[bit // 8] >> (7 - (bit % 8))) & 1


def _u16be(n: int) -> bytes:
    return n.to_bytes(2, "big")


# internal = sha256(0x01 || u16be(split_bit) || left || right)
#
# WHY split_bit IS IN THE HASH. Without it the bit each hop claims to test is not
# committed to by the node hash, so a host can relabel the hops while the chain still
# folds to the same root. That defeats non-membership: absence is proved by exhibiting a
# witness leaf that occupies the target's path, and "occupies the path" is judged by
# comparing bits at the positions the proof claims.
#
# AND WHY skiplen IS NOT, though it used to be. It is a FUNCTION of already-committed
# data: walking a proof root-to-leaf it is exactly split_bit - (previous split_bit + 1),
# which `_proof_steps_root_to_leaf` recomputed and compared rather than verifying against
# anything independent. Committing to a value the verifier derives binds nothing.
#
# Removing it is not tidiness. It makes a node's hash INDEPENDENT OF ITS DEPTH, so a
# subtree that re-parents keeps its hash -- and that is what fixes the two bugs this
# change is really about:
#
#   DELETE promoted the collapsing sibling unchanged. Correct for a leaf; for a BRANCH
#   the hash still committed to the depth it had just left, so the device derived a root
#   no honest rebuilder reproduces. Worse, `_proof_steps_root_to_leaf` then rejected every
#   proof through the re-parented node: one delete in three left the whole remaining tree
#   unverifiable on that device.
#
#   INSERT refused to splice above an existing branch, because splicing there re-parents
#   the branch below and its hash would have gone stale. Path compression means two keys
#   are only compared at the bits the tree actually branches on, so they can agree at all
#   of those and still part inside a compressed run -- the ordinary case for a random key.
#   Roughly a third of inserts were refused outright.
#
# Both are gone once the hash stops naming a depth: the spliced-off subtree and the
# promoted sibling both fold unchanged.
def internal_hash(split_bit: int, left: bytes, right: bytes) -> bytes:
    return _sha256d(b"\x01" + _u16be(split_bit) + left + right)


PROOF_ELEM_LEN = 34  # u16be(split_bit) || sibling(32B); was 36 with skiplen


def _parse_proof_elem(elem: bytes) -> tuple:
    if len(elem) != PROOF_ELEM_LEN:
        raise ValueError("invalid proof element length")
    return int.from_bytes(elem[0:2], "big"), bytes(elem[2:])


def _proof_steps_root_to_leaf(proof: list) -> list:
    """Check the proof describes a well-formed root-to-leaf path, and return its steps.

    Walking ROOT to leaf, the split bits must strictly increase. A proof that is reordered
    or has its bit claims shifted fails here before a single hash is computed. This also
    bounds the work: split_bit strictly increases and stays below 256, so no valid proof
    exceeds 256 elements however many the host sends.

    The skiplen consistency check that used to live here is gone with the field itself --
    it compared a host-supplied number against one derived from exactly these split bits.
    """
    steps = []
    start_bit = 0
    for elem in reversed(proof):
        split_bit, sibling = _parse_proof_elem(elem)
        if split_bit >= 256:
            raise ValueError("proof split_bit out of range")
        if split_bit < start_bit:
            raise ValueError("proof split bits are not strictly increasing")
        steps.append((split_bit, sibling))
        start_bit = split_bit + 1
    return steps


def reconstruct(start_hash: bytes, proof: list, entry_key_: bytes) -> bytes:
    """Walk proof from leaf toward root, rebuilding hashes. entry_key_ is the 32-byte
    trie path of the leaf the walk starts from."""
    _proof_steps_root_to_leaf(proof)
    node = start_hash
    for elem in proof:
        split_bit, sibling = _parse_proof_elem(elem)
        if addr_bit(entry_key_, split_bit) == 0:
            node = internal_hash(split_bit, node, sibling)
        else:
            node = internal_hash(split_bit, sibling, node)
    return node


def verify_proof(
    entry_key_: bytes,
    key_type: str,
    id_part,
    val_part,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify an MPT membership proof for the leaf (key_type, id_part, val_part) at
    entry_key against expected_root. The device forms the leaf from the two encoded
    parts it holds (commit -> leaf); no key is needed for this."""
    node = leaf_hash(entry_key_, key_type, id_part, val_part)
    node = reconstruct(node, proof, entry_key_)
    return node == expected_root


def verify_nonmembership(
    entry_key_: bytes,
    witness_entry_key: bytes,
    witness_commit: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify that entry_key is NOT in the tree.

    The witness leaf is supplied as two hashes -- (witness_entry_key,
    witness_commit) -- that occupies entry_key's path, revealing nothing about the
    witness's plaintext identifier or value. We verify: (0) every operand is exactly
    32 bytes; (1) the witness leaf rebuilt from the two hashes is in the tree;
    (2) witness_entry_key != entry_key; (3) both share the same bit at every proof
    position (closest leaf).

    (0) IS LOAD-BEARING and comes first. Checks (2) and (3) are both satisfied by a
    witness key that is the target with extra bytes glued on: it differs from the
    target, and routing reads bits 0..255 so it agrees at every branch bit. Since
    the leaf preimage concatenates key and commit with no boundary marker, K || C[0]
    with commit C[1:] hashes to the TARGET'S OWN leaf -- so the target's genuine
    membership proof passes as proof of its absence, and a host could hide any
    present entry on every read. `leaf_hash_of` refuses that too; rejecting it here
    stops the comparisons below from passing and reading as though the witness
    relationship were real.

    A wrong-width operand RAISES rather than returning False: it is a malformed
    message, not a claim that failed, and the two must not read alike."""
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
        steps = _proof_steps_root_to_leaf(proof)
    except ValueError:
        return False

    for split_bit, _sibling in steps:
        if addr_bit(entry_key_, split_bit) != addr_bit(witness_entry_key, split_bit):
            return False

    witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
    return reconstruct(witness_leaf, proof, witness_entry_key) == expected_root


def compute_new_root(
    entry_key_: bytes,
    old_leaf,
    new_leaf,
    proof: list,
    stored_root,
    witness_entry_key=None,
    witness_commit=None,
):
    """Verify the old state (old_leaf, proof) against stored_root, then compute the
    new root. `old_leaf`/`new_leaf` are (key_type, id_part, val_part) tuples the
    device produced, or None: old_leaf=None => INSERT, new_leaf=None => DELETE. Returns the new root
    (None if the tree becomes/stays empty), or raises ValueError if the old-state
    proof does not verify. INSERT's witness neighbour may belong to another app, so
    it is supplied privacy-preservingly as (witness_entry_key, witness_commit)."""
    inserting = old_leaf is None
    deleting = new_leaf is None
    if inserting and deleting:
        raise ValueError("old_leaf and new_leaf cannot both be empty")

    if inserting:
        if len(proof) == 0 and witness_entry_key is None:
            # INIT: tree was empty
            if stored_root is not None:
                raise ValueError("Tree is not empty; supply non-membership proof")
            return leaf_hash(entry_key_, new_leaf[0], new_leaf[1], new_leaf[2])

        if witness_entry_key is None or witness_commit is None:
            raise ValueError("witness_entry_key/witness_commit required for INSERT")

        # Lengths BEFORE any routing, on the same three operands and for the same reason
        # as verify_nonmembership. `addr_bit` indexes the key directly, so a short witness
        # raises IndexError out of the loop below -- an untyped crash where a protocol
        # error is the honest answer. `leaf_hash_of` does catch it, but only after that
        # loop has run.
        if (
            len(entry_key_) != 32
            or len(witness_entry_key) != 32
            or len(witness_commit) != 32
        ):
            raise ValueError("INSERT operands must be 32 bytes")

        if witness_entry_key == entry_key_:
            raise ValueError("witness_entry_key must differ from entry_key")

        steps = _proof_steps_root_to_leaf(proof)
        for split_bit, _sibling in steps:
            if addr_bit(entry_key_, split_bit) != addr_bit(witness_entry_key, split_bit):
                raise ValueError("Witness does not occupy target's path")

        witness_leaf = leaf_hash_of(witness_entry_key, witness_commit)
        witness_in_tree = reconstruct(witness_leaf, proof, witness_entry_key)
        if witness_in_tree != stored_root:
            raise ValueError("Non-membership proof invalid: witness not in tree")

        # Where the two paths part is computed HERE, never taken from the host: it decides
        # where the new leaf is spliced in, so a host-chosen value would let it graft the
        # entry somewhere structurally inconsistent with the rest of the tree.
        split_bit = None
        for b in range(256):
            if addr_bit(entry_key_, b) != addr_bit(witness_entry_key, b):
                split_bit = b
                break
        if split_bit is None:
            raise ValueError("entry_key and witness_entry_key are equal")

        # The new branch goes at `split_bit`, which is NOT necessarily below every branch
        # on the witness's path -- see the note on internal_hash. Everything the proof
        # branches on BELOW the splice point belongs to the subtree that re-parents under
        # the new branch, so fold it first; a node's hash no longer names its depth, so it
        # folds unchanged. This used to be an outright refusal.
        below = []
        idx = 0
        while idx < len(proof):
            sb, _sib = _parse_proof_elem(proof[idx])
            if sb == split_bit:
                # Unreachable: the agreement loop above rejects a proof that branches
                # where the keys differ, and split_bit is the first such bit. Explicit
                # because the silent alternative is two branches at one bit.
                raise ValueError("witness path already branches at the split bit")
            if sb < split_bit:
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

        new_leaf_t = leaf_hash(entry_key_, new_leaf[0], new_leaf[1], new_leaf[2])
        if addr_bit(entry_key_, split_bit) == 0:
            new_branch = internal_hash(split_bit, new_leaf_t, node)
        else:
            new_branch = internal_hash(split_bit, node, new_leaf_t)

        # above the splice the two keys agree, so folding by either path is the same
        return reconstruct(new_branch, proof[idx:], witness_entry_key)

    if deleting:
        if stored_root is None:
            raise ValueError("No Merkle root stored on device")
        current_leaf = leaf_hash(entry_key_, old_leaf[0], old_leaf[1], old_leaf[2])
        if reconstruct(current_leaf, proof, entry_key_) != stored_root:
            raise ValueError("Old value proof invalid")
        if len(proof) == 0:
            return None
        # The branch above collapses and the sibling takes its place -- UNCHANGED,
        # whatever it is. A node's hash no longer depends on its depth, so a re-parented
        # subtree keeps the hash the proof already committed to, and a leaf and a branch
        # behave identically here. Under the old format a branch sibling's hash went
        # stale the instant it moved, which is what made a third of deletes derive a root
        # no rebuilder agreed with.
        _split_bit, sibling_hash = _parse_proof_elem(proof[0])
        return reconstruct(sibling_hash, proof[1:], entry_key_)

    # UPDATE
    if stored_root is None:
        raise ValueError("No Merkle root stored on device")
    current_leaf = leaf_hash(entry_key_, old_leaf[0], old_leaf[1], old_leaf[2])
    if reconstruct(current_leaf, proof, entry_key_) != stored_root:
        raise ValueError("Old value proof invalid")
    new_leaf_h = leaf_hash(entry_key_, new_leaf[0], new_leaf[1], new_leaf[2])
    return reconstruct(new_leaf_h, proof, entry_key_)


def _multiproof_root(items, stored_root):
    """Recompute the trie root over a set of UPDATE items against `stored_root`, and
    return the new root, via a shape-preserving Merkle multiproof (§4.2).

    Each item is `(entry_key, old_leaf_hash, new_leaf_hash, proof)` where `proof` is
    the membership proof (bit, sibling) leaf→root of the OLD leaf against
    `stored_root`. All items must be UPDATES of leaves that already exist, so the
    trie SHAPE is unchanged and only leaf hashes move — the shared structure of the k
    proof paths is overlaid into one partial tree, external (boundary) siblings come
    from the proofs, and internal nodes shared by two batch leaves are recomputed from
    their children (never from a now-stale proof sibling).

    Crucially this uses proofs against the SINGLE common `stored_root` (exactly what
    the host serves for the whole batch), not per-leaf running roots. It VERIFIES by
    recomputing the old root from the overlay and requiring it to equal `stored_root`,
    then returns the new root with the new leaf hashes substituted. Raises ValueError
    on any inconsistency (mismatched branch bit / sibling / root)."""
    # Partial tree keyed by path = tuple of (bit, dir) taken from the root.
    branch = {}  # path -> branch_bit
    occupied = set()  # paths on some item's root→leaf walk (real nodes)
    old_leaf = {}  # path -> old leaf hash
    new_leaf = {}  # path -> new leaf hash
    sib_seen = {}  # path -> list of boundary sibling hashes recorded for it

    for ek, oh, nh, proof in items:
        path = ()
        occupied.add(path)
        for elem in reversed(proof):  # root → leaf order
            b, sib = _parse_proof_elem(elem)
            d = addr_bit(ek, b)
            if path in branch:
                if branch[path] != b:
                    raise ValueError("inconsistent branch metadata in batch multiproof")
            else:
                # The skiplen agreement that used to be checked here compared a
                # host-supplied number against one derived from the split bits either
                # side of it; `_proof_steps_root_to_leaf` (via reconstruct) already
                # enforces that those bits strictly increase, which is the whole of it.
                branch[path] = b
            sib_path = path + ((b, 1 - d),)
            sib_seen.setdefault(sib_path, []).append(sib)
            path = path + ((b, d),)
            occupied.add(path)
        old_leaf[path] = oh
        new_leaf[path] = nh

    # A non-occupied sibling is an EXTERNAL subtree: every proof that named it must
    # agree on its hash (this is the cross-proof consistency / verification step).
    for sib_path, sibs in sib_seen.items():
        if sib_path in occupied:
            continue
        for s in sibs:
            if s != sibs[0]:
                raise ValueError("inconsistent boundary sibling in batch multiproof")

    def child_hash(path, leaf_map):
        if path in occupied:
            return node_hash(path, leaf_map)
        sibs = sib_seen.get(path)
        if not sibs:
            raise ValueError("missing sibling in batch multiproof")
        return sibs[0]

    def node_hash(path, leaf_map):
        if path in leaf_map:
            return leaf_map[path]
        if path in branch:
            b = branch[path]
            left = child_hash(path + ((b, 0),), leaf_map)
            right = child_hash(path + ((b, 1),), leaf_map)
            return internal_hash(b, left, right)
        raise ValueError("dangling node in batch multiproof")

    if node_hash((), old_leaf) != stored_root:
        raise ValueError("batch pre-state proofs do not reconstruct the stored root")
    return node_hash((), new_leaf)


def compute_batch_root(stored_root, ops):
    """Apply a batch of leaf changes to `stored_root` and return the new root (`None`
    if the tree ends empty). Rejects a duplicate `entry_key` within the batch (§4.2).

    Each op is a 6-tuple `(entry_key, old_leaf, new_leaf, proof, witness_entry_key,
    witness_commit)` with the same semantics as `compute_new_root` (old_leaf=None =>
    INSERT, new_leaf=None => DELETE), and `proof` is the pre-state proof against
    `stored_root` (the single common base the host serves for the whole batch).

    - A single-op batch (n=1) delegates to the audited `compute_new_root`, so INIT /
      INSERT / UPDATE / DELETE all keep full generality.
    - A multi-op batch (n>1) currently supports **UPDATES only** (the trie shape is
      unchanged) and is folded by a shape-preserving multiproof (`_multiproof_root`)
      over the common `stored_root` — NOT a sequential running-root apply, which would
      wrongly reject leaf k's `stored_root`-proof. Insert/delete inside a multi-leaf
      batch is rejected here; use single-leaf commits for those until the general
      (shape-changing) multiproof lands.

    Per-leaf counter monotonicity (`C_new > C_old`, §4.5/F12) is enforced by the
    caller (`perform_batch`), not here."""
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
            op[0], op[1], op[2], op[3], stored_root,
            witness_entry_key=op[4], witness_commit=op[5],
        )

    items = []
    for ek, old_leaf, new_leaf, proof, w_ek, w_commit in ops:
        if old_leaf is None or new_leaf is None or w_ek is not None:
            raise ValueError(
                "multi-leaf batch supports UPDATES only; use single-leaf commits "
                "for insert/delete"
            )
        items.append(
            (
                ek,
                leaf_hash(ek, old_leaf[0], old_leaf[1], old_leaf[2]),
                leaf_hash(ek, new_leaf[0], new_leaf[1], new_leaf[2]),
                proof,
            )
        )
    if stored_root is None:
        raise ValueError("multi-leaf update batch requires a non-empty tree")
    return _multiproof_root(items, stored_root)
