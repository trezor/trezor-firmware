from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbGetOfflineOperations, AuthDbGetOfflineOperationsResponse


async def get_offline_operations(
    msg: AuthDbGetOfflineOperations,
) -> AuthDbGetOfflineOperationsResponse:
    """Return the current root/counter plus every queued operation, for upload.

    Pure read: no approval dialog, no storage mutation. One physical device
    only ever reports its own currently-active wallet's queue.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbGetOfflineOperationsResponse, AuthDbOfflineOperation
    from apps.authdb import _get_wallet_id

    wallet_id = await _get_wallet_id()

    current_root = authdb.get_root(wallet_id)
    counter = authdb.get_counter(wallet_id)
    queue = authdb.get_offline_queue(wallet_id)

    operations = [
        AuthDbOfflineOperation(
            sequence=sequence,
            address=address,
            old_value=old_value if old_value else None,
            new_value=new_value if new_value else None,
            mac=mac,
        )
        for sequence, address, old_value, new_value, mac in queue
    ]

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "get_offline_operations: wallet_id=%s counter=%d queue_len=%d",
            wallet_id, counter, len(operations),
        )

    return AuthDbGetOfflineOperationsResponse(
        current_root=current_root,
        counter=counter,
        wallet_id=wallet_id,
        operations=operations,
    )
