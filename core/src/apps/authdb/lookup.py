from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor import log
    from trezor.messages import AuthDbLookup, AuthDbLookupResponse


async def lookup(msg: AuthDbLookup) -> AuthDbLookupResponse:
    import storage.authdb as authdb
    from trezor.messages import AuthDbLookupResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id

    membership_query = msg.witness_address is None and msg.value is not None

    wallet_id = await _get_wallet_id()
    stored_root = authdb.get_root(wallet_id)

    if __debug__:
        from trezor import log
        from ubinascii import hexlify

        def _hex(b):
            return hexlify(b).decode() if b else "none"

        log.debug(
            __name__,
            "lookup: ENTER wallet_id=%s query=%s stored_root=%s stored_counter=%d",
            _hex(wallet_id),
            "membership" if membership_query else "non-membership",
            _hex(stored_root) if stored_root else "EMPTY",
            authdb.get_counter(wallet_id),
        )
        log.debug(
            __name__,
            "lookup:   address=%s value=%s counter=%s proof_len=%d",
            _hex(msg.address),
            _hex(msg.value),
            msg.counter if msg.counter is not None else "none",
            len(msg.proof),
        )
        log.debug(
            __name__,
            "lookup:   witness_address=%s witness_value=%s witness_counter=%s",
            _hex(msg.witness_address),
            _hex(msg.witness_value),
            msg.witness_counter if msg.witness_counter is not None else "none",
        )
        for i, elem in enumerate(msg.proof):
            log.debug(__name__, "lookup:   proof[%d]=%s", i, _hex(elem))

    if stored_root is None:
        # Empty tree: membership is trivially false, non-membership is trivially true.
        counter = authdb.get_counter(wallet_id)
        if __debug__:
            log.debug(
                __name__,
                "lookup: EMPTY tree -> valid=%s membership=%s counter=%d",
                not membership_query,
                membership_query,
                counter,
            )
        return AuthDbLookupResponse(
            valid=not membership_query,
            counter=counter,
            membership=membership_query,
            wallet_id=wallet_id,
        )

    if not membership_query:
        # Non-membership proof: prove witness is in tree, then verify address is absent
        if msg.witness_value is None or msg.witness_counter is None:
            raise DataError("witness_value and witness_counter required for non-membership proof")
        valid = _verify_nonmembership(
            msg.address, msg.witness_address, msg.witness_counter, msg.witness_value,
            msg.proof, stored_root,
        )
        membership = False
    else:
        # Membership proof
        if msg.counter is None:
            raise DataError("counter required for membership proof")
        valid = _verify_proof(msg.address, msg.counter, msg.value, msg.proof, stored_root)
        membership = True

    counter = authdb.get_counter(wallet_id)
    if __debug__:
        log.debug(
            __name__,
            "lookup: RESULT valid=%s membership=%s counter=%d (verified against stored_root=%s)",
            valid,
            membership,
            counter,
            _hex(stored_root),
        )

    return AuthDbLookupResponse(valid=valid, counter=counter, membership=membership, wallet_id=wallet_id)


def _verify_nonmembership(
    address: bytes,
    witness_address: bytes,
    witness_counter: int,
    witness_value: bytes,
    proof: list[bytes],
    expected_root: bytes,
) -> bool:
    """Verify that address is NOT in the tree.

    Thin wrapper kept for backwards compatibility (imported directly by
    core/tests/test_apps.authdb.py) -- the real implementation now lives in
    apps.authdb._mpt so update_leaf.py and the offline-sync handlers share
    the exact same audited logic.
    """
    from apps.authdb import _mpt

    return _mpt.verify_nonmembership(
        address, witness_address, witness_counter, witness_value, proof, expected_root
    )


def _verify_proof(
    address: bytes,
    counter: int,
    value: bytes,
    proof: list[bytes],
    expected_root: bytes,
) -> bool:
    """Verify an MPT (Merkle Patricia Trie) membership proof.

    Thin wrapper kept for backwards compatibility (imported directly by
    core/tests/test_apps.authdb.py) -- see apps.authdb._mpt for the shared
    implementation and docs/authdb.md for the hashing scheme / proof format.
    """
    from apps.authdb import _mpt

    return _mpt.verify_proof(address, counter, value, proof, expected_root)
