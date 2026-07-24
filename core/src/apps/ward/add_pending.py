from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDAddPending, WARDAddPendingAck


async def add_pending(msg: WARDAddPending) -> WARDAddPendingAck:
    """WARDAddPending wire handler (TA): drive the update through Core (ungated) into
    the WARD trust anchor, which verifies + queues the candidate. The device does
    NOT advance its counter here -- that happens at WARDConfirmCommit.
    """
    from trezor.messages import WARDAddPendingAck

    from apps.common import ward as core

    counter, wallet_id = await core.add_pending(
        msg.address,
        msg.old_value,
        msg.new_value,
        msg.new_counter,
        msg.proof,
        old_counter=msg.old_counter,
        witness_address=msg.witness_address,
        witness_counter=msg.witness_counter,
        witness_value=msg.witness_value,
    )

    return WARDAddPendingAck(counter=counter, wallet_id=wallet_id)
