from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbDeleteOfflineOperations, AuthDbDeleteOfflineOperationsResponse


async def delete_offline_operations(
    msg: AuthDbDeleteOfflineOperations,
) -> AuthDbDeleteOfflineOperationsResponse:
    """Delete every queued operation with sequence <= this device's own
    last_applied_sequence.

    Takes no input: the device is the sole source of truth for what it has
    actually applied, so garbage collection cannot be tricked into deleting
    an operation that was never really committed.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbDeleteOfflineOperationsResponse
    from apps.authdb import _get_wallet_id

    wallet_id = await _get_wallet_id()

    watermark = authdb.get_last_applied_sequence(wallet_id)
    deleted = authdb.delete_offline_operations_upto(wallet_id, watermark)
    remaining = authdb.offline_queue_count(wallet_id)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "delete_offline_operations: watermark=%d deleted=%d remaining=%d",
            watermark, deleted, remaining,
        )

    return AuthDbDeleteOfflineOperationsResponse(
        deleted_count=deleted, remaining_count=remaining
    )
