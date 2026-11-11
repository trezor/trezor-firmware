from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDServiceSync, WARDServiceSyncAck


async def service_sync(msg: WARDServiceSync) -> WARDServiceSyncAck:
    from trezor import utils
    from trezor.messages import WARDServiceSyncAck

    if utils.USE_WARD_SERVICE_CHANNEL:
        from storage import ward_head, ward_store
        from trezor.wire import ward_channel

        from apps.ward import keys

        if ward_channel.selected() is not None:
            await ward_channel.ensure_ready()
            wallet_id = await keys.get_wallet_id()
            _present, root = ward_head.root_get(wallet_id)
            return WARDServiceSyncAck(
                used_service=True,
                counter=ward_store.get_counter(wallet_id),
                root=root,
                ward_id=await keys.get_ward_id(),
            )
    return WARDServiceSyncAck(used_service=False)
