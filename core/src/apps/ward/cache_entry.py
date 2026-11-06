from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDCacheEntry, WARDCacheEntryAck


async def cache_entry(msg: WARDCacheEntry) -> WARDCacheEntryAck:
    """WARDCacheEntry wire handler (TA): pull and verify the entry at entry_key, then
    store it in its app's offline WARD store. Only whether a record was replaced goes
    back to the host.
    """
    from trezor.messages import WARDCacheEntryAck

    from apps.common import ward as core

    replaced, counter = await core.cache_entry(bytes(msg.entry_key), bool(msg.sticky))

    return WARDCacheEntryAck(replaced=replaced, counter=counter)
