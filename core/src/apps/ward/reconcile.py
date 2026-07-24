from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDReconcile, WARDReconcileAck


async def reconcile(msg: WARDReconcile) -> WARDReconcileAck:
    """WARDReconcile wire handler (TA): adopt the attested root as the device's
    authenticated state via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDReconcileAck

    from apps.common import ward as core

    counter, root, wallet_id, root_mac = await core.reconcile(msg.root)

    return WARDReconcileAck(
        counter=counter, new_root=root, wallet_id=wallet_id, root_mac=root_mac
    )
