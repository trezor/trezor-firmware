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
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac

    if not __debug__:
        raise DataError("AuthDbSetRoot is not available on production firmware")

    if len(msg.root) != authdb.ROOT_LENGTH:
        raise DataError("Root must be exactly 32 bytes")

    wallet_id = await _get_wallet_id()

    if msg.mac is None or msg.device_id is None:
        raise DataError("mac and device_id are required for AuthDbSetRoot")
    if msg.device_id != wallet_id:
        raise DataError("device_id mismatch")
    mac_key = await _derive_mac_key()
    if _compute_mac(mac_key, msg.root) != msg.mac:
        raise DataError("MAC verification failed")

    authdb.set_root(wallet_id, msg.root)
    counter = authdb.increment_counter(wallet_id)

    return AuthDbSetRootResponse(counter=counter, wallet_id=wallet_id)
