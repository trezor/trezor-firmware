from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDPerformRevert, WARDPerformRevertAck


async def perform_revert(msg: WARDPerformRevert) -> WARDPerformRevertAck:
    """WARDPerformRevert wire handler (TA): prepare a constrained one-step rollback
    (ward-design §8.2). The trust anchor verifies the host-supplied forward AuthCommit
    to prove the predecessor, checks the stuck head is the current authenticated head,
    and demotes with a forward-incrementing counter. Not advanced here.
    """
    from trezor.messages import WARDPerformRevertAck

    from apps.common import ward as core
    from apps.ward import service

    # Absent root fields mean the empty tree — map to the 32-byte MAC-preimage sentinel.
    stuck_root = msg.stuck_root if msg.stuck_root else service.EMPTY_ROOT_HASH
    prev_root = msg.prev_root if msg.prev_root else service.EMPTY_ROOT_HASH

    (
        counter,
        from_root,
        to_root,
        mac,
        head_mac,
        auth_revert,
        sig,
        wallet_id,
        ward_id,
    ) = await core.perform_revert(
        msg.stuck_counter, stuck_root, prev_root, msg.forward_auth_commit
    )

    return WARDPerformRevertAck(
        counter=counter,
        from_root=from_root,
        new_root=to_root,
        mac=mac,
        wallet_id=wallet_id,
        ward_id=ward_id,
        head_mac=head_mac,
        auth_revert=auth_revert,
        sig_commit=(sig if (sig and service.WARD_KSIG) else None),
    )
