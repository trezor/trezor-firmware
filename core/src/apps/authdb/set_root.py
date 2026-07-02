from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetRoot, AuthDbSetRootResponse

# DANGER: AuthDbSetRoot lets the host inject an arbitrary Merkle root into
# persistent storage. On production firmware the device must derive the root
# itself as the sole source of truth. Accepting an external root would let an
# attacker forge the database state. This handler is intentionally restricted
# to debug builds.


async def set_root(msg: AuthDbSetRoot) -> AuthDbSetRootResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbSetRootResponse
    from trezor.wire import DataError
    from apps.authdb import _get_identifier, _derive_mac_key, _compute_mac

    if not __debug__:
        raise DataError("AuthDbSetRoot is not available on production firmware")

    if len(msg.root) != authdb.ROOT_LENGTH:
        raise DataError("Root must be exactly 32 bytes")

    identifier = await _get_identifier()

    if msg.mac is not None and msg.device_id is not None:
        if msg.device_id != identifier:
            raise DataError("device_id mismatch")
        mac_key = await _derive_mac_key()
        if _compute_mac(mac_key, msg.root) != msg.mac:
            raise DataError("MAC verification failed")

    authdb.set_root(identifier, msg.root)
    counter = authdb.increment_counter(identifier)

    return AuthDbSetRootResponse(counter=counter, identifier=identifier)
