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

    The device computes the new root and stores it, incrementing the GLOBAL root
    counter by 1. The changed leaf is stamped with that new global counter, so
    new_counter must equal (current root counter + 1). The host never supplies a
    root directly, so this handler is safe on production firmware. The transition
    logic lives in apps.authdb._mpt.compute_new_root().
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbUpdateLeafResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    wallet_id = await _get_wallet_id()
    root_mac_key = await _derive_mac_key(b"root_mac")

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
        for i, elem in enumerate(proof):
            log.debug(__name__, "update_leaf:   proof[%d]=%s", i, _hex(elem))

    # Global-counter stamp: the leaf is stamped with the NEW global counter, which is the
    # current root counter + 1. Reject a stale/incorrect stamp (also enforces anti-rollback
    # on the leaf version).
    current_counter = authdb.get_counter(wallet_id)
    expected_new_counter = current_counter + 1
    if new_counter != expected_new_counter:
        raise DataError("new_counter must equal current global counter + 1")

    stored_root = authdb.get_root(wallet_id)
    if __debug__:
        log.debug(
            __name__,
            "update_leaf:   stored_root=%s current_counter=%d -> computing new root",
            _hex(stored_root) if stored_root else "EMPTY",
            current_counter,
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

    # TODO: show address+new_value confirmation dialog when UI ready (production).

    # Persist root+counter as a single atomic storage write (see
    # storage/authdb.py's commit_root_and_counter()) -- root and counter always move
    # together, so a crash can never leave one advanced without the other.
    counter = authdb.commit_root_and_counter(wallet_id, new_root)

    if __debug__:
        log.debug(
            __name__,
            "update_leaf: COMMITTED new_root=%s counter=%d",
            _hex(new_root) if new_root else "EMPTY(tree now empty)",
            counter,
        )

    # Root-attestation token: binds wallet_id and the global counter (not just the root),
    # so the stored (new_root, counter, mac) triple is a self-contained, verifiable
    # attestation -- it is what AuthDbSetRoot verifies when re-installing a root.
    new_root_mac = (
        _compute_mac(root_mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )

    if __debug__:
        log.debug(
            __name__,
            "update_leaf: RESPONSE counter=%d new_root=%s root_mac=%s",
            counter,
            _hex(new_root) if new_root else "none",
            _hex(new_root_mac),
        )
    return AuthDbUpdateLeafResponse(
        counter=counter,
        new_root=new_root,
        wallet_id=wallet_id,
        mac=new_root_mac,
    )
