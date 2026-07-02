from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetCacheEntry, AuthDbSetCacheEntryResponse


async def set_cache_entry(msg: AuthDbSetCacheEntry) -> AuthDbSetCacheEntryResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbSetCacheEntryResponse
    from trezor.wire import DataError
    from apps.authdb import _get_device_id

    try:
        authdb.set_cache_entry(msg.address, msg.label, msg.data_mac)
    except ValueError as e:
        raise DataError(str(e))

    device_id = await _get_device_id()
    identifier_crc = int.from_bytes(device_id[:4], "big")
    return AuthDbSetCacheEntryResponse(identifier_crc=identifier_crc)
