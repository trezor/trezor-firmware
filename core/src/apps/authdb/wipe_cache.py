from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbWipeCache, AuthDbWipeCacheResponse


async def wipe_cache(msg: AuthDbWipeCache) -> AuthDbWipeCacheResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbWipeCacheResponse

    authdb.wipe_cache()
    return AuthDbWipeCacheResponse()
