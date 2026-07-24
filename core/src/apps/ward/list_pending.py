from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDListPendingEdits, WARDListPendingEditsAck


async def list_pending(msg: WARDListPendingEdits) -> WARDListPendingEditsAck:
    """WARDListPendingEdits wire handler (TA): return the device's queued
    pending-edit addresses via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDListPendingEditsAck

    from apps.common import ward as core

    addresses, wallet_id = await core.list_pending()

    return WARDListPendingEditsAck(addresses=addresses, wallet_id=wallet_id)
