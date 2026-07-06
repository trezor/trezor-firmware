from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbSetRoot, AuthDbSetRootResponse

# `mac` is REQUIRED (no longer optional/conditionally debug-only as a whole
# handler). Two cases:
#
#   mac == 32 zero bytes: a plain unauthenticated root injection, accepted
#   ONLY on debug builds. Production firmware must otherwise derive every
#   root itself (AuthDbUpdateLeaf / AuthDbApplyOfflineOperations), never
#   accept one directly -- so the zero-mac path is rejected outright on
#   production firmware.
#
#   Any other mac: verified exactly like AuthDbFastForwardRoot -- device_id
#   must match this wallet's wallet_id, counter must be strictly greater
#   than the current counter (anti-rollback), and
#   mac == HMAC(root_mac_key, wallet_id||counter||root). This is safe on
#   PRODUCTION firmware too: the only way to legitimately hold a verifying
#   mac is to already have one a device itself produced
#   (AuthDbUpdateLeafResponse.mac / AuthDbApplyOfflineOperationsResponse.root_mac)
#   -- root_mac_key never leaves the device, derived via SLIP-21 from the
#   wallet's seed+passphrase, so a host cannot forge one for a root of its
#   own choosing.
#
# After the root/counter are installed by either path, `operations` (if any)
# are replayed via apps.authdb._replay.replay_operations() -- the identical
# verification AuthDbApplyOfflineOperations uses -- so a caller can install
# an attested state and replay this wallet's own pending queue on top of it
# in one round trip.


async def set_root(msg: AuthDbSetRoot) -> AuthDbSetRootResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbSetRootResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb._replay import replay_operations

    if len(msg.root) != authdb.ROOT_LENGTH:
        raise DataError("root must be exactly 32 bytes")

    wallet_id = await _get_wallet_id()
    ZERO_MAC = b"\x00" * 32

    if __debug__ and msg.mac == ZERO_MAC:
        # Debug-only unauthenticated root injection. root+counter land in a
        # single atomic write (see storage/authdb.py's commit_root_and_counter()).
        authdb.commit_root_and_counter(wallet_id, msg.root)
    else:
        if msg.mac == ZERO_MAC:
            raise DataError("zero mac is only accepted in debug builds")
        if msg.device_id is None or msg.counter is None:
            raise DataError("device_id and counter are required with a non-zero mac")
        if msg.device_id != wallet_id:
            raise DataError("device_id mismatch")

        current_counter = authdb.get_counter(wallet_id)
        if msg.counter <= current_counter:
            raise DataError("counter must be greater than the current counter")

        root_mac_key = await _derive_mac_key(b"root_mac")
        expected_mac = _compute_mac(
            root_mac_key, wallet_id, msg.counter.to_bytes(4, "big"), msg.root
        )
        if expected_mac != msg.mac:
            raise DataError("MAC verification failed")

        # Jump straight to the attested counter (not merely +1) -- same
        # reasoning as AuthDbFastForwardRoot: the MAC check above already
        # proved this exact (wallet_id, counter, root) triple was produced
        # by a device that reached it one increment at a time itself.
        authdb.commit_root_and_counter_value(wallet_id, msg.root, msg.counter)

    # Replay this wallet's own pending offline queue (if any) on top of the
    # just-installed root, using the identical logic
    # AuthDbApplyOfflineOperations uses. Runs unconditionally -- even for
    # the debug zero-mac path -- since replay's own verification is what
    # keeps this safe, not how the root itself was authenticated.
    applied_count, new_root, counter, last_applied_sequence, root_mac = await replay_operations(
        wallet_id, msg.operations
    )

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "set_root: wallet_id=%s counter=%d applied_count=%d",
            wallet_id, counter, applied_count,
        )

    return AuthDbSetRootResponse(
        counter=counter,
        wallet_id=wallet_id,
        new_root=new_root,
        applied_count=applied_count,
        last_applied_sequence=last_applied_sequence,
        root_mac=root_mac,
    )
