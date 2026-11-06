from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDCacheImport, WARDCacheImportAck


async def cache_import(msg: WARDCacheImport) -> WARDCacheImportAck:
    """WARDCacheImport wire handler (TA): load backed-up entries sealed by this wallet
    into the offline cache, each checked against WARD by a proof the device pulls."""
    from trezor.messages import WARDCacheImportAck

    from apps.common import ward as core

    imported, skipped = await core.import_cache([bytes(b) for b in msg.entries])
    return WARDCacheImportAck(imported=imported, skipped=skipped)
