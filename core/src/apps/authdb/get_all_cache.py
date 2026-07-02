from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbGetAllCache, AuthDbGetAllCacheResponse


async def get_all_cache(msg: AuthDbGetAllCache) -> AuthDbGetAllCacheResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbGetAllCacheResponse, AuthDbGetAllCacheEntry

    entries = [
        AuthDbGetAllCacheEntry(address=addr, label=label, data_mac=data_mac)
        for addr, label, data_mac in authdb.get_all_cache_entries()
    ]
    return AuthDbGetAllCacheResponse(entries=entries)
