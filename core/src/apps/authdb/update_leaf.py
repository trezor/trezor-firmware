from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbUpdateLeaf, AuthDbUpdateLeafResponse


async def update_leaf(msg: AuthDbUpdateLeaf) -> AuthDbUpdateLeafResponse:
    """Atomically verify old state and update a leaf in the Merkle tree.

    Operations:
      UPDATE : old_value non-empty, new_value non-empty, membership proof
      DELETE : old_value non-empty, new_value empty,     membership proof
      INSERT : old_value empty,     new_value non-empty, non-membership proof
      INIT   : old_value empty,     new_value non-empty, proof empty, no witness

    The device computes the new root and stores it.  The host never supplies a
    root directly, so this handler is safe on production firmware. The actual
    transition logic lives in apps.authdb._mpt.compute_new_root(), shared with
    apply_offline_operations.py.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbUpdateLeafResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    wallet_id = await _get_wallet_id()
    root_mac_key = await _derive_mac_key(b"root_mac")
    leaf_approval_mac_key = await _derive_mac_key(b"leaf_approval")


    address = msg.address
    old_value = msg.old_value   # empty bytes = address absent from tree
    new_value = msg.new_value   # empty bytes = delete
    proof = msg.proof

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "update_leaf: address=%s old_value=%s new_value=%s proof_len=%d",
            address, old_value, new_value, len(proof),
        )

    # Leaf hashes for old and new state (used for MAC verification and auth_mac)
    # For INIT (old_value empty) use zero hash; for DELETE (new_value empty) use zero hash
    ZERO_HASH = b"\x00" * 32
    old_leaf_hash = _mpt.leaf_hash(address, old_value) if old_value else ZERO_HASH
    new_leaf_hash = _mpt.leaf_hash(address, new_value) if new_value else ZERO_HASH

    # Verify MAC-based pre-authorization when supplied by the host
    if msg.mac is not None and msg.device_id is not None:
        if msg.device_id != wallet_id:
            raise DataError("device_id mismatch")
        expected_mac = _compute_mac(leaf_approval_mac_key, old_leaf_hash, new_leaf_hash)
        if expected_mac != msg.mac:
            if __debug__:
                from trezor import log
                log.debug(
                    __name__,
                    "update_leaf: pre-approved MAC mismatch expected=%s got=%s",
                    expected_mac, msg.mac,
                )
            raise DataError("MAC verification failed")
        if __debug__:
            from trezor import log
            log.debug(__name__, "update_leaf: pre-approved MAC verified ok")
        # pre-authorized — confirmation dialog skipped
    else:
        pass  # TODO: show address+new_value confirmation dialog when UI ready (production)

    stored_root = authdb.get_root(wallet_id)
    try:
        new_root = _mpt.compute_new_root(
            address, old_value, new_value, proof, stored_root,
            msg.witness_address, msg.witness_value,
        )
    except ValueError as e:
        raise DataError(str(e))

    # Persist the new root.
    #
    # increment_counter() requires the wallet's storage record to already
    # exist, and clear_root() deletes that record outright (wallet_id, root
    # AND counter). So on a DELETE that empties the tree, the counter must be
    # bumped BEFORE clearing the root (the record still exists from the prior
    # operation); for every other transition, set_root() -- which creates the
    # record on a first-ever INIT -- must run first instead. Doing this in
    # the other order raises "No record for wallet_id" on every delete-to-
    # empty-tree call.
    if new_root is None:
        counter = authdb.increment_counter(wallet_id)
        authdb.clear_root(wallet_id)
    else:
        authdb.set_root(wallet_id, new_root)
        counter = authdb.increment_counter(wallet_id)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "update_leaf: new_root=%s counter=%d",
            new_root if new_root else "empty",
            counter,
        )

    # Root-attestation token: binds wallet_id and counter (not just the root)
    # so it can be safely replayed via AuthDbFastForwardRoot -- see that
    # message's proto doc for why the counter must be inside the MAC.
    new_root_mac = (
        _compute_mac(root_mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )
    
    update_leaf_auth_mac = _compute_mac(leaf_approval_mac_key, old_leaf_hash, new_leaf_hash) if __debug__ else None
    
    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "update_leaf: auto-approve new_mac=%s (reuse as mac= in next pre-approved call)",
            new_root_mac,
        )
    return AuthDbUpdateLeafResponse(
        counter=counter,
        new_root=new_root,
        wallet_id=wallet_id,
        mac=new_root_mac,
        auth_mac=update_leaf_auth_mac,
    )
