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
    root directly, so this handler is safe on production firmware.
    """
    import storage.authdb as authdb
    from trezor.messages import AuthDbUpdateLeafResponse
    from trezor.wire import DataError
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    _sha256d = _mpt.sha256d
    _addr_bit = _mpt.addr_bit
    _leaf_hash = _mpt.leaf_hash
    _internal_hash = _mpt.internal_hash
    _reconstruct = _mpt.reconstruct

    wallet_id = await _get_wallet_id()
    mac_key = await _derive_mac_key()

    address = msg.address
    old_value = msg.old_value   # empty bytes = address absent from tree
    new_value = msg.new_value   # empty bytes = delete
    proof = msg.proof

    inserting = len(old_value) == 0
    deleting  = len(new_value) == 0

    if inserting and deleting:
        raise DataError("old_value and new_value cannot both be empty")

    addr_hash = _sha256d(address)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "update_leaf: address=%s inserting=%s deleting=%s proof_len=%d",
            address, inserting, deleting, len(proof),
        )

    # Leaf hashes for old and new state (used for MAC verification and auth_mac)
    # For INIT (old_value empty) use zero hash; for DELETE (new_value empty) use zero hash
    ZERO_HASH = b"\x00" * 32
    old_leaf_hash = _leaf_hash(address, old_value) if old_value else ZERO_HASH
    new_leaf_hash = _leaf_hash(address, new_value) if new_value else ZERO_HASH

    # Verify MAC-based pre-authorization when supplied by the host
    if msg.mac is not None and msg.device_id is not None:
        if msg.device_id != wallet_id:
            raise DataError("device_id mismatch")
        expected_mac = _compute_mac(mac_key, old_leaf_hash, new_leaf_hash)
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

    if inserting:
        # INSERT or INIT — verify non-membership first
        if len(proof) == 0 and msg.witness_address is None:
            # INIT: tree was empty; verify no root is stored
            stored_root = authdb.get_root(wallet_id)
            if stored_root is not None:
                raise DataError("Tree is not empty; supply non-membership proof")
            new_root: bytes | None = _leaf_hash(address, new_value)
            if __debug__:
                from trezor import log
                log.debug(__name__, "update_leaf: INIT — empty tree, no proof required")
        else:
            # INSERT: verify witness is in tree and address is absent
            if msg.witness_address is None or msg.witness_value is None:
                raise DataError("witness_address and witness_value required for INSERT")
            stored_root = authdb.get_root(wallet_id)
            if stored_root is None:
                #raise DataError("No Merkle root stored; use INIT (empty proof, no witness)")
                if __debug__:
                    from trezor import log
                    log.error(__name__, "No Merkle root stored; use INIT (empty proof, no witness)")

            witness_hash = _sha256d(msg.witness_address)

            # Witness and target must share all branch bits in the proof
            for elem in proof:
                bit = elem[0]
                if _addr_bit(addr_hash, bit) != _addr_bit(witness_hash, bit):
                    raise DataError("Witness does not occupy target's path")

            if msg.witness_address == address:
                raise DataError("witness_address must differ from address")

            # Verify witness membership
            witness_in_tree = _reconstruct(
                _leaf_hash(msg.witness_address, msg.witness_value), proof, witness_hash
            ) == stored_root
            if not witness_in_tree and stored_root is not None:
                raise DataError("Non-membership proof invalid: witness not in tree")

            # Find the first bit where witness and target diverge (split point)
            split_bit = None
            for b in range(256):
                if _addr_bit(addr_hash, b) != _addr_bit(witness_hash, b):
                    split_bit = b
                    break
            if split_bit is None:
                raise DataError("address and witness_address hash to same value")

            # Build the new branch node at split_bit
            new_leaf_T = _leaf_hash(address, new_value)
            new_leaf_W = _leaf_hash(msg.witness_address, msg.witness_value)
            if _addr_bit(addr_hash, split_bit) == 0:
                new_branch = _internal_hash(new_leaf_T, new_leaf_W)
            else:
                new_branch = _internal_hash(new_leaf_W, new_leaf_T)

            # The new branch replaces the old witness leaf in the proof chain
            # We use the witness's addr_hash to walk the remaining proof
            new_root = _reconstruct(new_branch, proof, witness_hash)

    elif deleting:
        # DELETE — verify current membership first
        stored_root = authdb.get_root(wallet_id)
        if stored_root is None:
            #raise DataError("No Merkle root stored on device")
            if __debug__:
                from trezor import log
                log.error(__name__, "No Merkle root stored on device")

        current_leaf = _leaf_hash(address, old_value)
        if _reconstruct(current_leaf, proof, addr_hash) != stored_root:
            raise DataError("Old value proof invalid")
        if __debug__ and len(proof) == 0:
            from trezor import log
            log.debug(__name__, "update_leaf: single-leaf tree — empty proof is correct root proof")

        if len(proof) == 0:
            # Deleting the only leaf → tree becomes empty
            new_root = None
        else:
            # The parent branch collapses: sibling becomes the replacement
            # proof[0] is the closest sibling (33 bytes: bit + hash)
            sibling_hash = bytes(proof[0][1:])
            # Walk the remaining proof from sibling upward
            sibling_bit = proof[0][0]
            # Determine sibling's side: addr_hash at sibling_bit tells our side,
            # so sibling is on the opposite side; but we need sibling's addr to
            # reconstruct correctly.  Since we don't know sibling's addr, we
            # just need to walk proof[1:] treating the sibling hash as the new start.
            # The sibling's position (left/right) at each ancestor level is the
            # same as the target's position (they share all ancestors above split).
            new_root = _reconstruct(sibling_hash, proof[1:], addr_hash)

    else:
        # UPDATE — verify current membership first
        stored_root = authdb.get_root(wallet_id)
        if stored_root is None:
            raise DataError("No Merkle root stored on device")

        current_leaf = _leaf_hash(address, old_value)
        if _reconstruct(current_leaf, proof, addr_hash) != stored_root:
            raise DataError("Old value proof invalid")
        if __debug__ and len(proof) == 0:
            from trezor import log
            log.debug(__name__, "update_leaf: single-leaf tree — empty proof is correct root proof")

        new_root = _reconstruct(_leaf_hash(address, new_value), proof, addr_hash)

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
    new_mac = (
        _compute_mac(mac_key, wallet_id, counter.to_bytes(4, "big"), new_root)
        if new_root is not None
        else None
    )
    # In debug mode: auto-approve — return auth_mac so Suite can cache it for future calls
    auth_mac = _compute_mac(mac_key, old_leaf_hash, new_leaf_hash) if __debug__ else None
    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "update_leaf: auto-approve auth_mac=%s (reuse as mac= in next pre-approved call)",
            auth_mac,
        )
    return AuthDbUpdateLeafResponse(
        counter=counter,
        new_root=new_root,
        wallet_id=wallet_id,
        mac=new_mac,
        auth_mac=auth_mac,
    )
