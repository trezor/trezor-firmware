from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDDiscardPending, WARDDiscardPendingAck


async def discard_pending(msg: WARDDiscardPending) -> WARDDiscardPendingAck:
    """WARDDiscardPending wire handler (TA): abandon the current wallet's queued
    pending edit (via Core -> WARD trust anchor), unblocking the depth-1 queue.
    """
    from trezor.messages import WARDDiscardPendingAck

    from apps.common import ward as core

    discarded_address, wallet_id = await core.discard_pending()

    return WARDDiscardPendingAck(
        discarded_address=discarded_address, wallet_id=wallet_id
    )
