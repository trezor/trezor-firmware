from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbFastForwardRoot, AuthDbFastForwardRootResponse


async def fast_forward_root(
    msg: AuthDbFastForwardRoot,
) -> AuthDbFastForwardRootResponse:
    """Fast-forward this wallet's root to a state some device already attested to.

    Safe on production firmware, unlike AuthDbSetRoot, because `mac` is not a
    host-chosen value: it can only be a root-attestation token a device
    already computed and returned (AuthDbUpdateLeafResponse.mac or
    AuthDbApplyOfflineOperationsResponse.root_mac). mac_key is derived from
    the wallet's seed, not the physical device, so the same token verifies on
    every physical device that has unlocked this wallet -- Suite can relay a
    token from device A to fast-forward device B, but cannot mint a new one.

    `counter` and `wallet_id` are bound INSIDE the mac preimage; the device
    only trusts the counter it decodes from the verified mac for its
    monotonicity check, never a bare sibling field -- otherwise a host could
    pair a genuine old attestation with a forged, unauthenticated higher
    counter to bypass the anti-rollback check.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbFastForwardRootResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac

    if len(msg.new_root) != authdb.ROOT_LENGTH:
        raise DataError("new_root must be exactly 32 bytes")

    wallet_id = await _get_wallet_id()
    if msg.wallet_id != wallet_id:
        raise DataError("wallet_id mismatch")

    current_counter = authdb.get_counter(wallet_id)
    if msg.counter <= current_counter:
        raise DataError("counter must be greater than the current counter")

    mac_key = await _derive_mac_key(b"root_mac")
    expected_mac = _compute_mac(
        mac_key, wallet_id, msg.counter.to_bytes(4, "big"), msg.new_root
    )
    if expected_mac != msg.mac:
        raise DataError("MAC verification failed")

    # Jump straight to the attested counter value (not merely +1) -- the MAC
    # check above already proved this exact (wallet_id, counter, new_root)
    # triple was produced by a device that reached it one increment at a
    # time itself. root+counter land in a single atomic storage write (see
    # storage/authdb.py's commit_root_and_counter_value()), so a crash
    # between them can't happen; even if it could, replaying the identical
    # MAC-attested call again is self-healing (same inputs, same result).
    authdb.commit_root_and_counter_value(wallet_id, msg.new_root, msg.counter)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "fast_forward_root: wallet_id=%s counter=%d->%d",
            wallet_id, current_counter, msg.counter,
        )

    return AuthDbFastForwardRootResponse(
        counter=authdb.get_counter(wallet_id),
        new_root=msg.new_root,
        wallet_id=wallet_id,
    )
