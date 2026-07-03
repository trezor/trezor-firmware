from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbApplyOfflineOperations, AuthDbApplyOfflineOperationsResponse, AuthDbRebasedOperation


async def apply_offline_operations(
    msg: AuthDbApplyOfflineOperations,
) -> AuthDbApplyOfflineOperationsResponse:
    """Apply a batch of host-rebased offline operations.

    The device independently verifies each operation's MAC and Merkle proof
    and computes the resulting root itself; it never accepts a host-supplied
    root. Processing stops at the first operation that fails verification or
    is not the immediate next expected sequence -- committed state can never
    skip over an unresolved conflict. No approval dialog is shown: approval
    already happened when the operation was queued (see
    queue_offline_operation.py); the MAC is the cryptographic record of it.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbApplyOfflineOperationsResponse
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    wallet_id = await _get_wallet_id()
    mac_key = await _derive_mac_key()

    expected_seq = authdb.get_last_applied_sequence(wallet_id) + 1
    current_root = authdb.get_root(wallet_id)
    applied_count = 0

    for op in msg.operations:
        old_value = op.old_value if op.old_value else b""
        new_value = op.new_value if op.new_value else b""

        if op.sequence != expected_seq:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "apply_offline_operations: sequence gap, expected=%d got=%d, stopping",
                    expected_seq, op.sequence,
                )
            break

        ZERO_HASH = b"\x00" * 32
        old_leaf_hash = _mpt.leaf_hash(op.address, old_value) if old_value else ZERO_HASH
        new_leaf_hash = _mpt.leaf_hash(op.address, new_value) if new_value else ZERO_HASH
        expected_mac = _compute_mac(
            mac_key, op.sequence.to_bytes(4, "big"), old_leaf_hash, new_leaf_hash
        )
        if expected_mac != op.mac:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "apply_offline_operations: MAC mismatch at sequence=%d, stopping",
                    op.sequence,
                )
            break

        try:
            new_root = _mpt.compute_new_root(
                op.address, old_value, new_value, op.proof, current_root,
                op.witness_address, op.witness_value,
            )
        except ValueError as e:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "apply_offline_operations: rejected at sequence=%d: %s",
                    op.sequence, str(e),
                )
            break

        # Persist this operation's transition before moving to the next, so
        # a power loss mid-batch always leaves root/counter/
        # last_applied_sequence mutually consistent (same ordering fix as
        # update_leaf.py: bump counter before clear_root on delete-to-empty).
        if new_root is None:
            authdb.increment_counter(wallet_id)
            authdb.clear_root(wallet_id)
        else:
            authdb.set_root(wallet_id, new_root)
            authdb.increment_counter(wallet_id)
        authdb.set_last_applied_sequence(wallet_id, op.sequence)

        current_root = new_root
        applied_count += 1
        expected_seq += 1

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "apply_offline_operations: applied_count=%d new_root=%s",
            applied_count, current_root if current_root else "empty",
        )

    final_counter = authdb.get_counter(wallet_id)
    # Root-attestation token, same formula/purpose as update_leaf.py's mac:
    # lets this device's replayed state be fast-forwarded onto ANY other
    # physical device sharing this wallet, without redoing the whole replay.
    root_mac = (
        _compute_mac(mac_key, wallet_id, final_counter.to_bytes(4, "big"), current_root)
        if current_root is not None
        else None
    )

    return AuthDbApplyOfflineOperationsResponse(
        applied_count=applied_count,
        new_root=current_root,
        counter=final_counter,
        last_applied_sequence=authdb.get_last_applied_sequence(wallet_id),
        wallet_id=wallet_id,
        root_mac=root_mac,
    )
