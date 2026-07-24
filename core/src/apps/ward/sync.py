from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDSync, WARDSyncAck


async def sync(msg: WARDSync) -> WARDSyncAck:
    """WARDSync wire handler (TA): begin a sync round (mint the per-round
    nonce) via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDSyncAck

    from apps.common import ward as core

    nonce, version, wallet_id = await core.sync()

    return WARDSyncAck(nonce=nonce, version=version, wallet_id=wallet_id)
