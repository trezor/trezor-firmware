"""Shared Merkle Patricia Trie hash/proof primitives.

Used by update_leaf.py, lookup.py, queue_offline_operation.py, and
apply_offline_operations.py so the proof-verification logic -- including the
INIT/INSERT/UPDATE/DELETE state machine in compute_new_root() -- is
implemented and audited exactly once, the property docs/authdb.md calls out
as the reason production firmware never accepts a host-supplied root. See
docs/authdb.md for the hashing scheme and proof format.

Leaf counter: every leaf hash is now `sha256d(0x00||address||counter(4B BE)||value)`
-- counter is a first-class, cryptographically-committed per-address version
number (docs/authdb-sync-proposal.md Part 1), not just text an application
happens to embed inside the opaque `value` blob. INIT/INSERT require
new_counter == 1; UPDATE requires new_counter == old_counter + 1, enforced
here so a "conflict is only a counter race, not a real content conflict" can
be a device-checked fact rather than an unverified host claim.
"""


def sha256d(data: bytes) -> bytes:
    from trezor.crypto.hashlib import sha256

    return sha256(data).digest()


def addr_bit(addr_hash: bytes, bit: int) -> int:
    return (addr_hash[bit // 8] >> (7 - (bit % 8))) & 1


def leaf_hash(address: bytes, counter: int, value: bytes) -> bytes:
    return sha256d(b"\x00" + address + counter.to_bytes(4, "big") + value)


def internal_hash(left: bytes, right: bytes) -> bytes:
    return sha256d(b"\x01" + left + right)


def reconstruct(start_hash: bytes, proof: list, addr_hash: bytes) -> bytes:
    """Walk proof from leaf toward root, rebuilding hashes."""
    node = start_hash
    for elem in proof:
        bit = elem[0]
        sibling = bytes(elem[1:])
        if addr_bit(addr_hash, bit) == 0:
            node = internal_hash(node, sibling)
        else:
            node = internal_hash(sibling, node)
    return node


def verify_proof(
    address: bytes,
    counter: int,
    value: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify an MPT membership proof for (address, counter, value) against expected_root."""
    addr_hash = sha256d(address)
    node = leaf_hash(address, counter, value)
    node = reconstruct(node, proof, addr_hash)
    return node == expected_root


def verify_nonmembership(
    address: bytes,
    witness_address: bytes,
    witness_counter: int,
    witness_value: bytes,
    proof: list,
    expected_root: bytes,
) -> bool:
    """Verify that address is NOT in the tree.

    The caller supplies a witness leaf (witness_address, witness_counter,
    witness_value) that occupies address's path in the tree. We verify:
      1. The witness is in the tree (membership proof against stored root).
      2. witness_address != address.
      3. witness_address and address share the same bit-value at every bit
         position that appears in the proof (they diverge only after the
         deepest branch, i.e. the witness is truly the closest leaf to
         address).
    """
    if witness_address == address:
        return False

    addr_hash = sha256d(address)
    witness_hash = sha256d(witness_address)

    for elem in proof:
        bit = elem[0]
        if addr_bit(addr_hash, bit) != addr_bit(witness_hash, bit):
            return False

    return verify_proof(witness_address, witness_counter, witness_value, proof, expected_root)


def compute_new_root(
    address: bytes,
    old_counter: int,
    old_value: bytes,
    new_counter: int,
    new_value: bytes,
    proof: list,
    stored_root,
    witness_address=None,
    witness_counter=None,
    witness_value=None,
):
    """Verify (old_counter, old_value, proof) against stored_root, enforce the
    leaf-counter transition rule, then compute the new root.

    Returns the new root (None if the tree becomes/stays empty), or raises
    ValueError if the old-state proof does not verify, or if the counter
    transition is invalid. This is the single shared implementation of the
    INIT/INSERT/UPDATE/DELETE state machine -- update_leaf.py,
    apply_offline_operations.py, and set_root.py's replay path all call this
    rather than each maintaining their own copy, so a bug fixed here is fixed
    for every mutating RPC at once.

    Counter rule: INIT/INSERT require new_counter == 1. UPDATE requires
    new_counter == old_counter + 1 -- the actual cryptographic enforcement
    that makes "this conflict is only a counter race" a device-checkable
    fact. DELETE only needs old_counter (to reconstruct the current leaf for
    the membership proof); new_counter is ignored, since a deleted leaf is
    virtual (empty value) and the counter becomes irrelevant once a leaf is
    virtual.

    Deliberately STRICTER than update_leaf.py's original inline logic in
    one edge case: the witness-membership check for INSERT now runs
    unconditionally (`witness_in_tree != stored_root`), including when
    stored_root is None. The original inline code only raised when
    `not witness_in_tree and stored_root is not None`, which silently
    skipped the check entirely on an empty tree -- i.e. an INSERT into an
    empty tree that incorrectly supplies a witness+proof instead of using
    the INIT path (empty proof, no witness) was never actually validated.
    Since stored_root is None makes any real witness_in_tree hash compare
    unequal anyway, this only changes behavior for that one malformed-input
    edge case, always toward rejecting it -- never toward accepting
    something that was previously rejected.
    """
    inserting = len(old_value) == 0
    deleting = len(new_value) == 0
    if inserting and deleting:
        raise ValueError("old_value and new_value cannot both be empty")

    addr_hash = sha256d(address)

    if inserting:
        if new_counter != 1:
            raise ValueError("new_counter must be 1 for INIT/INSERT")

        if len(proof) == 0 and witness_address is None:
            # INIT: tree was empty
            if stored_root is not None:
                raise ValueError("Tree is not empty; supply non-membership proof")
            return leaf_hash(address, new_counter, new_value)

        if witness_address is None or witness_counter is None or witness_value is None:
            raise ValueError("witness_address/witness_counter/witness_value required for INSERT")
        if witness_address == address:
            raise ValueError("witness_address must differ from address")

        witness_hash = sha256d(witness_address)
        for elem in proof:
            bit = elem[0]
            if addr_bit(addr_hash, bit) != addr_bit(witness_hash, bit):
                raise ValueError("Witness does not occupy target's path")

        witness_in_tree = reconstruct(
            leaf_hash(witness_address, witness_counter, witness_value), proof, witness_hash
        )
        if witness_in_tree != stored_root:
            raise ValueError("Non-membership proof invalid: witness not in tree")

        split_bit = None
        for b in range(256):
            if addr_bit(addr_hash, b) != addr_bit(witness_hash, b):
                split_bit = b
                break
        if split_bit is None:
            raise ValueError("address and witness_address hash to same value")

        new_leaf_t = leaf_hash(address, new_counter, new_value)
        new_leaf_w = leaf_hash(witness_address, witness_counter, witness_value)
        if addr_bit(addr_hash, split_bit) == 0:
            new_branch = internal_hash(new_leaf_t, new_leaf_w)
        else:
            new_branch = internal_hash(new_leaf_w, new_leaf_t)
        return reconstruct(new_branch, proof, witness_hash)

    if deleting:
        if stored_root is None:
            raise ValueError("No Merkle root stored on device")
        current_leaf = leaf_hash(address, old_counter, old_value)
        if reconstruct(current_leaf, proof, addr_hash) != stored_root:
            raise ValueError("Old value proof invalid")
        if len(proof) == 0:
            return None
        sibling_hash = bytes(proof[0][1:])
        return reconstruct(sibling_hash, proof[1:], addr_hash)

    # UPDATE
    if new_counter != old_counter + 1:
        raise ValueError("new_counter must be old_counter + 1 for UPDATE")
    if stored_root is None:
        raise ValueError("No Merkle root stored on device")
    current_leaf = leaf_hash(address, old_counter, old_value)
    if reconstruct(current_leaf, proof, addr_hash) != stored_root:
        raise ValueError("Old value proof invalid")
    return reconstruct(leaf_hash(address, new_counter, new_value), proof, addr_hash)
