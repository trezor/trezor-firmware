from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetRoot, AuthDbSetRootResponse

# `mac` is REQUIRED. Two cases:
#
#   mac == 32 zero bytes: a plain unauthenticated root injection, accepted
#   ONLY on debug builds. Production firmware must otherwise derive every root
#   itself (AuthDbUpdateLeaf), never accept one directly -- so the zero-mac
#   path is rejected outright on production firmware.
#
#   Any other mac: wallet_id must match this wallet's wallet_id, counter must
#   be strictly greater than the current counter (anti-rollback), and
#   mac == HMAC(root_mac_key, wallet_id||counter||root). Safe on PRODUCTION
#   firmware: the only way to hold a verifying mac is to already have one a
#   device itself produced (AuthDbUpdateLeafResponse.mac) -- root_mac_key never
#   leaves the device, so a host cannot forge one for a root of its choosing.


async def set_root(msg: AuthDbSetRoot) -> AuthDbSetRootResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbSetRootResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac

    if len(msg.root) != authdb.ROOT_LENGTH:
        raise DataError("root must be exactly 32 bytes")

    wallet_id = await _get_wallet_id()
    ZERO_MAC = b"\x00" * 32

    if __debug__ and msg.mac == ZERO_MAC:
        # Debug-only unauthenticated root injection. root+counter land in a
        # single atomic write (see storage/authdb.py's commit_root_and_counter()).
        counter = authdb.commit_root_and_counter(wallet_id, msg.root)
    else:
        if msg.mac == ZERO_MAC:
            raise DataError("zero mac is only accepted in debug builds")
        if msg.wallet_id is None or msg.counter is None:
            raise DataError("wallet_id and counter are required with a non-zero mac")
        if msg.wallet_id != wallet_id:
            raise DataError("wallet_id mismatch")

        current_counter = authdb.get_counter(wallet_id)
        if msg.counter <= current_counter:
            raise DataError("counter must be greater than the current counter")

        root_mac_key = await _derive_mac_key(b"root_mac")
        expected_mac = _compute_mac(
            root_mac_key, wallet_id, msg.counter.to_bytes(4, "big"), msg.root
        )
        if expected_mac != msg.mac:
            raise DataError("MAC verification failed")

        # Jump straight to the attested counter (not merely +1): the MAC check
        # above already proved this exact (wallet_id, counter, root) triple was
        # produced by a device that reached it one increment at a time itself.
        authdb.commit_root_and_counter_value(wallet_id, msg.root, msg.counter)
        counter = msg.counter

    root_mac_key = await _derive_mac_key(b"root_mac")
    new_root = authdb.get_root(wallet_id)
    root_mac = (
        _compute_mac(root_mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )

    if __debug__:
        from trezor import log
        log.debug(__name__, "set_root: wallet_id=%s counter=%d", wallet_id, counter)

    return AuthDbSetRootResponse(
        counter=counter,
        wallet_id=wallet_id,
        new_root=new_root,
        root_mac=root_mac,
    )
