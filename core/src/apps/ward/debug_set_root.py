from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDDebugSetRoot, WARDDebugSetRootAck


async def debug_set_root(msg: WARDDebugSetRoot) -> WARDDebugSetRootAck:
    """WARDDebugSetRoot wire handler (TA): DEBUG-ONLY root injection via the WARD
    trust anchor (through Core). Rejected on production firmware.
    """
    from trezor.messages import WARDDebugSetRootAck

    from apps.common import ward as core

    counter, new_root, wallet_id, root_mac = await core.debug_set_root(msg.root)

    return WARDDebugSetRootAck(
        counter=counter, new_root=new_root, wallet_id=wallet_id, root_mac=root_mac
    )
