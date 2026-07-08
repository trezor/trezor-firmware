from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbInit, AuthDbInitResponse


async def init(msg: AuthDbInit) -> AuthDbInitResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbInitResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb._qm import verify_qm_counter

    wallet_id = await _get_wallet_id()

    # 1. Verify the QM-signed counter and adopt it as the anti-rollback ceiling.
    if not verify_qm_counter(wallet_id, msg.qm_counter, msg.qm_signature):
        raise DataError("QM signature verification failed")

    # The QM counter must never go backwards (anti-rollback).
    current_qm = authdb.get_qm_counter(wallet_id)
    if msg.qm_counter < current_qm:
        raise DataError("qm_counter is older than the stored qm_last_counter")

    # 2. If a root is supplied (Evolu holds one), verify it before installing.
    root: bytes | None = None
    counter: int | None = None
    if msg.root is not None:
        if len(msg.root) != authdb.ROOT_LENGTH:
            raise DataError("root must be exactly 32 bytes")
        if msg.counter is None or msg.root_mac is None:
            raise DataError("counter and root_mac are required with a root")
        # The QM and the stored root must agree on where the wallet is.
        if msg.counter != msg.qm_counter:
            raise DataError("root counter must equal qm_counter")
        # The root must be one THIS device produced (its own root_mac).
        root_mac_key = await _derive_mac_key(b"root_mac")
        expected_mac = _compute_mac(
            root_mac_key, wallet_id, msg.counter.to_bytes(4, "big"), msg.root
        )
        if expected_mac != msg.root_mac:
            raise DataError("root MAC verification failed")
        root = msg.root
        counter = msg.counter

    # Single atomic write: qm_last_counter (always) + (root, counter) when supplied.
    authdb.commit_init(wallet_id, msg.qm_counter, root, counter)

    # Build the response from the now-current stored state.
    stored_counter = authdb.get_counter(wallet_id)
    stored_root = authdb.get_root(wallet_id)
    root_mac_key = await _derive_mac_key(b"root_mac")
    stored_root_mac = (
        _compute_mac(
            root_mac_key, wallet_id, stored_counter.to_bytes(4, "big"), stored_root
        )
        if stored_root is not None
        else None
    )

    if __debug__:
        from trezor import log

        log.debug(
            __name__,
            "init: wallet_id=%s qm_last_counter=%d counter=%d",
            wallet_id,
            msg.qm_counter,
            stored_counter,
        )

    return AuthDbInitResponse(
        qm_last_counter=msg.qm_counter,
        wallet_id=wallet_id,
        counter=stored_counter,
        root=stored_root,
        root_mac=stored_root_mac,
    )
