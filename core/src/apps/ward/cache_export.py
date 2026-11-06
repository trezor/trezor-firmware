from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDCacheExport, WARDCacheExportAck


async def cache_export(msg: WARDCacheExport) -> WARDCacheExportAck:
    """WARDCacheExport wire handler (TA): back up the offline cache's WARD entries as
    blobs sealed to this wallet."""
    from trezor.messages import WARDCacheExportAck

    from apps.ward import service

    return WARDCacheExportAck(entries=[entry for entry in await service.export_cache()])
