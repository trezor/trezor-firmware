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
    old_counter = msg.old_counter if msg.old_counter else 0
    new_counter = msg.new_counter
    proof = msg.proof

    if __debug__:
        from trezor import log
        from ubinascii import hexlify

        def _hex(b):
            return hexlify(b).decode() if b else "none"

        # Classify the operation for readability (matches the docstring's 4 cases).
        if not old_value and new_value:
            op = "INIT" if len(proof) == 0 and msg.witness_address is None else "INSERT"
        elif old_value and not new_value:
            op = "DELETE"
        elif old_value and new_value:
            op = "UPDATE"
        else:
            op = "INVALID(empty->empty)"
        log.debug(
            __name__,
            "update_leaf: ENTER op=%s wallet_id=%s address=%s",
            op, _hex(wallet_id), _hex(address),
        )
        log.debug(
            __name__,
            "update_leaf:   old_value=%s (counter=%d) new_value=%s (counter=%d) proof_len=%d",
            _hex(old_value), old_counter, _hex(new_value), new_counter, len(proof),
        )
        log.debug(
            __name__,
            "update_leaf:   witness_address=%s witness_value=%s witness_counter=%s mac=%s device_id=%s",
            _hex(msg.witness_address),
            _hex(msg.witness_value),
            msg.witness_counter if msg.witness_counter is not None else "none",
            _hex(msg.mac),
            _hex(msg.device_id),
        )
        for i, elem in enumerate(proof):
            log.debug(__name__, "update_leaf:   proof[%d]=%s", i, _hex(elem))

    # Leaf hashes for old and new state (used for MAC verification and auth_mac)
    # For INIT (old_value empty) use zero hash; for DELETE (new_value empty) use zero hash
    ZERO_HASH = b"\x00" * 32
    old_leaf_hash = _mpt.leaf_hash(address, old_counter, old_value) if old_value else ZERO_HASH
    new_leaf_hash = _mpt.leaf_hash(address, new_counter, new_value) if new_value else ZERO_HASH

    if __debug__:
        log.debug(
            __name__,
            "update_leaf:   old_leaf_hash=%s new_leaf_hash=%s",
            _hex(old_leaf_hash), _hex(new_leaf_hash),
        )

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
    if __debug__:
        log.debug(
            __name__,
            "update_leaf:   stored_root=%s -> computing new root",
            _hex(stored_root) if stored_root else "EMPTY",
        )
    try:
        new_root = _mpt.compute_new_root(
            address, old_counter, old_value, new_counter, new_value, proof, stored_root,
            witness_address=msg.witness_address,
            witness_counter=msg.witness_counter,
            witness_value=msg.witness_value,
        )
    except ValueError as e:
        if __debug__:
            log.error(__name__, "update_leaf: REJECTED by compute_new_root: %s", str(e))
        raise DataError(str(e))

    # Persist root+counter as a single atomic storage write (see
    # storage/authdb.py's commit_root_and_counter()) -- root and counter
    # always move together, so a crash can never leave one advanced without
    # the other, the same property commit_applied_operation() gives the
    # offline-sync apply path.
    counter = authdb.commit_root_and_counter(wallet_id, new_root)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "update_leaf: COMMITTED new_root=%s counter=%d",
            _hex(new_root) if new_root else "EMPTY(tree now empty)",
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
            "update_leaf: RESPONSE counter=%d new_root=%s root_mac=%s auth_mac=%s",
            counter,
            _hex(new_root) if new_root else "none",
            _hex(new_root_mac),
            _hex(update_leaf_auth_mac),
        )
    return AuthDbUpdateLeafResponse(
        counter=counter,
        new_root=new_root,
        wallet_id=wallet_id,
        mac=new_root_mac,
        auth_mac=update_leaf_auth_mac,
    )
