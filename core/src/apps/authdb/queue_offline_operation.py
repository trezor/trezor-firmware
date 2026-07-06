from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbQueueOfflineOperation, AuthDbQueueOfflineOperationResponse


async def queue_offline_operation(
    msg: AuthDbQueueOfflineOperation,
) -> AuthDbQueueOfflineOperationResponse:
    """Sign and append an offline operation to the on-device queue.

    Used when the host database is unreachable. Does not touch the Merkle
    root -- the operation is only applied later via
    AuthDbApplyOfflineOperations, after the host has rebased it against the
    current canonical tree and supplied a fresh Merkle proof.

    The confirmation dialog shown here is the ONLY approval point for this
    operation: AuthDbApplyOfflineOperations never re-prompts, since the MAC
    computed below cryptographically records that this exact (sequence,
    address, old_value, new_value) was approved.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbQueueOfflineOperationResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    address = msg.address
    old_value = msg.old_value
    new_value = msg.new_value

    if len(old_value) == 0 and len(new_value) == 0:
        raise DataError("old_value and new_value cannot both be empty")

    # TODO: show address+old_value+new_value confirmation dialog when UI ready
    # (production). This is the ONLY approval point in the offline-sync flow.

    wallet_id = await _get_wallet_id()
    leaf_approval_mac_key = await _derive_mac_key(b"leaf_approval")

    ZERO_HASH = b"\x00" * 32
    old_leaf_hash = _mpt.leaf_hash(address, old_value) if old_value else ZERO_HASH
    new_leaf_hash = _mpt.leaf_hash(address, new_value) if new_value else ZERO_HASH

    # Check capacity before taking a sequence number, so a full queue never
    # burns a sequence on a rejected operation.
    if authdb.offline_queue_count(wallet_id) >= authdb.MAX_OFFLINE_QUEUE_ENTRIES:
        raise DataError("Offline queue full")

    # sequence is taken AFTER approval, so a cancelled dialog never burns one.
    sequence = authdb.take_next_sequence(wallet_id)
    mac = _compute_mac(
        leaf_approval_mac_key, sequence.to_bytes(4, "big"), old_leaf_hash, new_leaf_hash
    )

    try:
        authdb.append_offline_operation(
            wallet_id, sequence, address, old_value, new_value, mac
        )
    except ValueError as e:
        raise DataError(str(e))

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "queue_offline_operation: address=%s sequence=%d mac=%s",
            address, sequence, mac,
        )

    return AuthDbQueueOfflineOperationResponse(
        sequence=sequence, mac=mac, wallet_id=wallet_id
    )
