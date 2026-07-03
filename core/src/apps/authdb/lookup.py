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
    if stored_root is None:
        # Empty tree: membership is trivially false, non-membership is trivially true.
        counter = authdb.get_counter(wallet_id)
        return AuthDbLookupResponse(
            valid=not membership_query,
            counter=counter,
            membership=membership_query,
            wallet_id=wallet_id,
        )

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "lookup: address=%s proof_len=%d witness=%s membership_query=%s",
            msg.address,
            len(msg.proof),
            msg.witness_address if msg.witness_address else "none",
            membership_query,
        )

    if not membership_query:
        # Non-membership proof: prove witness is in tree, then verify address is absent
        if msg.witness_value is None:
            raise DataError("witness_value required for non-membership proof")
        valid = _verify_nonmembership(
            msg.address, msg.witness_address, msg.witness_value, msg.proof, stored_root
        )
        membership = False
    else:
        # Membership proof
        valid = _verify_proof(msg.address, msg.value, msg.proof, stored_root)
        membership = True

    if __debug__:
        from trezor import log
        log.debug(__name__, "lookup: result valid=%s membership=%s", valid, membership)

    counter = authdb.get_counter(wallet_id)
    return AuthDbLookupResponse(valid=valid, counter=counter, membership=membership, wallet_id=wallet_id)


def _verify_nonmembership(
    address: bytes,
    witness_address: bytes,
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
        address, witness_address, witness_value, proof, expected_root
    )


def _verify_proof(
    address: bytes,
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

    return _mpt.verify_proof(address, value, proof, expected_root)
