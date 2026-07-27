from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDQueueUpdate, WARDQueueUpdateAck


async def queue_update(msg: WARDQueueUpdate) -> WARDQueueUpdateAck:
    """WARDQueueUpdate wire handler (TA): queue an edit INTENT (via Core -> WARD
    trust anchor). Pull model: intent-only, no proof. Shows old -> new on a trusted
    screen and returns the pending_id ONLY on user approval; the device pulls the
    proof and computes the candidate later, at WARDPerformUpdate.
    """
    from trezor.messages import WARDQueueUpdateAck

    from apps.common import ward as core

    counter, pending_id, wallet_id = await core.queue_update(
        msg.address, msg.old_value or b"", msg.new_value
    )

    return WARDQueueUpdateAck(
        counter=counter, pending_id=pending_id, wallet_id=wallet_id
    )
