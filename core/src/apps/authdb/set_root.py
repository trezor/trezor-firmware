from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetRoot, AuthDbSetRootResponse

# DANGER (no-mac path): AuthDbSetRoot lets the host inject an arbitrary
# Merkle root into persistent storage. On production firmware the device
# must derive the root itself as the sole source of truth. Accepting an
# external root would let an attacker forge the database state, so the
# no-mac path is restricted to debug builds.
#
# mac/device_id are OPTIONAL, not required: if supplied, they're verified as
# a debug convenience (so a caller that happens to hold a well-formed
# root_mac can exercise this path deterministically), but this handler
# itself stays debug-only regardless of whether a mac is present -- unlike
# AuthDbFastForwardRoot, which is the actual production-safe path for
# replaying a device-issued root attestation. (Regression note: an earlier
# revision made mac/device_id unconditionally required here, which broke
# every bare debug call; restored to optional to match the original intent.)
#
# NOTE: this handler's own mac preimage is HMAC(root_mac_key, root) --
# root-only, unlike AuthDbFastForwardRoot's HMAC(root_mac_key, wallet_id ||
# counter || root). That means a mac produced by AuthDbUpdateLeafResponse.mac
# or AuthDbApplyOfflineOperationsResponse.root_mac will NOT verify here (it's
# shaped for AuthDbFastForwardRoot instead) -- known, harmless inconsistency
# since this whole handler is debug-only either way; not fixed here to avoid
# duplicating AuthDbFastForwardRoot's anti-rollback counter-jump logic.


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

    if msg.mac is not None or msg.device_id is not None:
        if msg.mac is None or msg.device_id is None:
            raise DataError("mac and device_id must both be supplied, or neither")
        if msg.device_id != wallet_id:
            raise DataError("device_id mismatch")
        root_mac_key = await _derive_mac_key(b"root_mac")
        if _compute_mac(root_mac_key, msg.root) != msg.mac:
            raise DataError("MAC verification failed")
    # else: no mac supplied -- plain debug-only unauthenticated root injection.

    authdb.set_root(wallet_id, msg.root)
    counter = authdb.increment_counter(wallet_id)

    return AuthDbSetRootResponse(counter=counter, wallet_id=wallet_id)
