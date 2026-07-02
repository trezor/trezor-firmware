from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetDeviceId, AuthDbSetDeviceIdResponse

# DEBUG ONLY — same restriction as AuthDbSetRoot / AuthDbClearRoot.


async def set_device_id(msg: AuthDbSetDeviceId) -> AuthDbSetDeviceIdResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbSetDeviceIdResponse
    from trezor.wire import DataError

    if not __debug__:
        raise DataError("AuthDbSetDeviceId is not available on production firmware")

    if len(msg.device_id) != 32:
        raise DataError("device_id must be exactly 32 bytes")

    authdb.set_device_id_override(msg.device_id)
    return AuthDbSetDeviceIdResponse(device_id=msg.device_id)
