from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetRoot, AuthDbSetRootResponse


async def set_root(msg: AuthDbSetRoot) -> AuthDbSetRootResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbSetRootResponse
    from trezor.wire import DataError

    if len(msg.root) != authdb.ROOT_LENGTH:
        raise DataError("Root must be exactly 32 bytes")

    authdb.set_root(msg.root)
    counter = authdb.increment_counter()

    return AuthDbSetRootResponse(counter=counter)
