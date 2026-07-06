from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbApplyOfflineOperations, AuthDbApplyOfflineOperationsResponse, AuthDbRebasedOperation


async def apply_offline_operations(
    msg: AuthDbApplyOfflineOperations,
) -> AuthDbApplyOfflineOperationsResponse:
    """Apply a batch of host-rebased offline operations.

    Thin wrapper around apps.authdb._replay.replay_operations() -- see that
    module for the actual verification/apply logic, shared with
    AuthDbSetRoot's embedded `operations` replay so both RPCs run exactly the
    same code.
    """
    from trezor.messages import AuthDbApplyOfflineOperationsResponse
    from apps.authdb import _get_wallet_id
    from apps.authdb._replay import replay_operations

    wallet_id = await _get_wallet_id()
    applied_count, new_root, counter, last_applied_sequence, root_mac = await replay_operations(
        wallet_id, msg.operations
    )

    return AuthDbApplyOfflineOperationsResponse(
        applied_count=applied_count,
        new_root=new_root,
        counter=counter,
        last_applied_sequence=last_applied_sequence,
        wallet_id=wallet_id,
        root_mac=root_mac,
    )
