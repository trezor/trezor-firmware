from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDListPendingEdits, WARDListPendingEditsAck


async def pending(msg: WARDListPendingEdits) -> WARDListPendingEditsAck:
    """WARDListPendingEdits wire handler (TA): return the device's queued
    pending-edit addresses via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDListPendingEditsAck

    from apps.common import ward as core

    pending_ids, addresses, wallet_id, ward_id = await core.pending()

    return WARDListPendingEditsAck(
        addresses=addresses, pending_ids=pending_ids, wallet_id=wallet_id, ward_id=ward_id
    )
