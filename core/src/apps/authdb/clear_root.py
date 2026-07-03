from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbClearRoot, AuthDbClearRootResponse

# DANGER: debug builds only — same reasoning as AuthDbSetRoot.


async def clear_root(msg: AuthDbClearRoot) -> AuthDbClearRootResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbClearRootResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id

    if not __debug__:
        raise DataError("AuthDbClearRoot is not available on production firmware")

    wallet_id = await _get_wallet_id()
    authdb.clear_root(wallet_id)
    return AuthDbClearRootResponse(wallet_id=wallet_id)
