from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDSync, WARDSyncAck


async def sync(msg: WARDSync) -> WARDSyncAck:
    """WARDSync wire handler (TA): begin a sync round (mint the per-round
    nonce) via the WARD trust anchor (through Core).
    """
    from trezor.messages import WARDSyncAck

    from apps.common import ward as core

    nonce, version, _wallet_id, ward_id = await core.sync()
    from storage import ward_head, ward_store

    present, root = ward_head.root_get(_wallet_id)
    counter = ward_store.get_counter(_wallet_id)

    return WARDSyncAck(
        nonce=nonce,
        version=version,
        ward_id=ward_id,
        counter=counter,
        root=root,
        root_known=present or counter == 0,
        service_bound=_service_bound(),
    )


def _service_bound() -> bool:
    from trezor import utils

    if utils.USE_WARD_SERVICE_CHANNEL:
        from trezor.wire.ward_channel import selected

        return selected() is not None
    return False
