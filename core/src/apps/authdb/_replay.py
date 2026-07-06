"""Shared offline-operation replay logic.

Extracted from apply_offline_operations.py so AuthDbApplyOfflineOperations
and AuthDbSetRoot's embedded `operations` replay (installing an attested
root/counter and then immediately replaying the device's own pending queue
on top of it, in one call) share exactly one implementation of "verify each
op's MAC and proof, apply strictly in order, stop at the first conflict."
"""


async def replay_operations(wallet_id: bytes, operations: list):
    """Apply a batch of host-rebased offline operations against wallet_id's
    CURRENT root (whatever it is at the time this is called -- the caller is
    responsible for having already installed any fast-forwarded root first).

    The device independently verifies each operation's MAC and Merkle proof
    and computes the resulting root itself; it never accepts a host-supplied
    root. Processing stops at the first operation that fails verification or
    is not the immediate next expected sequence -- committed state can never
    skip over an unresolved conflict. No approval dialog is shown here:
    approval already happened when the operation was queued (see
    queue_offline_operation.py); the MAC is the cryptographic record of it.

    Returns (applied_count, current_root, final_counter, last_applied_sequence, root_mac).
    root_mac is the same root-attestation-token formula update_leaf.py uses,
    None if the tree ends up empty.
    """
    import storage.authdb as authdb
    from apps.authdb import _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    leaf_approval_mac_key = await _derive_mac_key(b"leaf_approval")
    root_mac_key = await _derive_mac_key(b"root_mac")
    expected_seq = authdb.get_last_applied_sequence(wallet_id) + 1
    current_root = authdb.get_root(wallet_id)
    applied_count = 0

    ZERO_HASH = b"\x00" * 32

    for op in operations:
        old_value = op.old_value if op.old_value else b""
        new_value = op.new_value if op.new_value else b""
        old_counter = op.old_counter if op.old_counter else 0
        new_counter = op.new_counter

        if op.sequence != expected_seq:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "replay_operations: sequence gap, expected=%d got=%d, stopping",
                    expected_seq, op.sequence,
                )
            break

        old_leaf_hash = _mpt.leaf_hash(op.address, old_counter, old_value) if old_value else ZERO_HASH
        new_leaf_hash = _mpt.leaf_hash(op.address, new_counter, new_value) if new_value else ZERO_HASH
        expected_mac = _compute_mac(
            leaf_approval_mac_key, op.sequence.to_bytes(4, "big"), old_leaf_hash, new_leaf_hash
        )
        if expected_mac != op.mac:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "replay_operations: MAC mismatch at sequence=%d, stopping",
                    op.sequence,
                )
            break

        try:
            new_root = _mpt.compute_new_root(
                op.address, old_counter, old_value, new_counter, new_value, op.proof, current_root,
                witness_address=op.witness_address,
                witness_counter=op.witness_counter,
                witness_value=op.witness_value,
            )
        except ValueError as e:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "replay_operations: rejected at sequence=%d: %s",
                    op.sequence, str(e),
                )
            break

        # Persist this operation's transition as ONE atomic storage write --
        # root, counter, and last_applied_sequence together via
        # commit_applied_operation() -- so a power loss mid-batch can never
        # leave them mutually inconsistent. Three separate writes could leave
        # root already advanced with no record of it anywhere, and no way to
        # retry: the retry's proof is built for the now-superseded old root,
        # so it fails forever, permanently stranding this wallet's queue.
        authdb.commit_applied_operation(wallet_id, new_root, op.sequence)

        current_root = new_root
        applied_count += 1
        expected_seq += 1

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "replay_operations: applied_count=%d new_root=%s",
            applied_count, current_root if current_root else "empty",
        )

    final_counter = authdb.get_counter(wallet_id)
    # Root-attestation token, same formula/purpose as update_leaf.py's mac:
    # lets this device's replayed state be fast-forwarded onto ANY other
    # physical device sharing this wallet, without redoing the whole replay.
    root_mac = (
        _compute_mac(root_mac_key, wallet_id, final_counter.to_bytes(4, "big"), current_root)
        if current_root is not None
        else None
    )

    return (
        applied_count,
        current_root,
        final_counter,
        authdb.get_last_applied_sequence(wallet_id),
        root_mac,
    )
