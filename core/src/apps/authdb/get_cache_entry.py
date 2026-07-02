from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbGetCacheEntry, AuthDbGetCacheEntryResponse


async def get_cache_entry(msg: AuthDbGetCacheEntry) -> AuthDbGetCacheEntryResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbGetCacheEntryResponse

    label, data_mac = authdb.get_cache_entry(msg.address)
    found = label is not None or data_mac is not None
    return AuthDbGetCacheEntryResponse(found=found, label=label, data_mac=data_mac)
