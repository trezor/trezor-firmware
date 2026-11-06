from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDQueueUpdate, WARDQueueUpdateAck


async def queue(msg: WARDQueueUpdate) -> WARDQueueUpdateAck:
    """WARDQueueUpdate wire handler (TA): queue an edit INTENT (via Core -> WARD
    trust anchor). Pull model: intent-only, no proof. Shows the new value on a trusted
    screen and returns the pending_id ONLY on user approval; the device pulls the
    proof and computes the candidate later, at WARDPerformUpdate.
    """
    from trezor.messages import WARDQueueUpdateAck

    from apps.common import ward as core
    from apps.ward.caller import host_caller

    # The host does not choose the domain, key type or slot: refused unless absent or
    # equal to what the WARD service fixes for host-driven labels.
    caller = host_caller(msg.app_id, msg.key_type, msg.device_id)
    pending_id, _wallet_id = await core.queue(
        caller, bytes(msg.address), bytes(msg.new_value), delete=bool(msg.delete)
    )

    return WARDQueueUpdateAck(pending_id=pending_id)
